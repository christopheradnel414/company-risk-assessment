import json
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.src.models.response import ModuleStatus, SearchResult
from app.src.search_modules.base import BaseSearchModule, SearchModuleResult
from app.src.services.llm_service import LLMService, _LLM_RETRY


@pytest.fixture
def llm_service():
    with patch("app.src.services.llm_service.get_settings"), patch("app.src.services.llm_service.AsyncOpenAI"):
        service = LLMService()
    service._client = MagicMock()
    service._model = "test-model"
    return service


def _mock_response(content: dict):
    response = MagicMock()
    response.choices[0].message.content = json.dumps(content)
    response.choices[0].finish_reason = "stop"
    return response


def _connection_error():
    return openai.APIConnectionError(request=MagicMock())


class MockModule(BaseSearchModule):
    module_id = "mock"
    module_name = "Mock"
    description = "mock"
    output_schema = {"type": "object", "additionalProperties": True}
    system_prompt = "You are a test assistant."

    async def fetch(self, context) -> SearchModuleResult:
        return SearchModuleResult(raw_data={})


class TestStructuredChat:
    @pytest.mark.asyncio
    async def test_raises_if_schema_is_empty(self, llm_service):
        with pytest.raises(ValueError, match="schema"):
            await llm_service._structured_chat("sys", "user", schema={})

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_success(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"key": "value"})
        )

        result = await llm_service._structured_chat("sys", "user", schema={"type": "object"})

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_retries_on_connection_error_and_succeeds(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(side_effect=[
            _connection_error(),
            _mock_response({"key": "value"}),
        ])

        result = await llm_service._structured_chat("sys", "user", schema={"type": "object"})

        assert result == {"key": "value"}
        assert llm_service._client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout_error_and_succeeds(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(side_effect=[
            openai.APITimeoutError(request=MagicMock()),
            _mock_response({"result": "ok"}),
        ])

        result = await llm_service._structured_chat("sys", "user", schema={"type": "object"})

        assert result == {"result": "ok"}
        assert llm_service._client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            side_effect=_connection_error()
        )

        with pytest.raises(openai.APIConnectionError):
            await llm_service._structured_chat("sys", "user", schema={"type": "object"})

        assert llm_service._client.chat.completions.create.call_count == _LLM_RETRY + 1

    @pytest.mark.asyncio
    async def test_retries_on_empty_content(self, llm_service):
        empty_response = MagicMock()
        empty_response.choices[0].message.content = ""
        empty_response.choices[0].finish_reason = "length"

        llm_service._client.chat.completions.create = AsyncMock(side_effect=[
            empty_response,
            _mock_response({"key": "value"}),
        ])

        result = await llm_service._structured_chat("sys", "user", schema={"type": "object"})

        assert result == {"key": "value"}


class TestParseModuleResult:
    @pytest.mark.asyncio
    async def test_returns_error_if_raw_result_has_error(self, llm_service):
        module = MockModule()
        raw = SearchModuleResult(error="Fetch failed")

        result = await llm_service.parse_module_result(module, raw)

        assert result == {"error": "Fetch failed"}
        llm_service._client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_parsed_data_on_success(self, llm_service):
        module = MockModule()
        raw = SearchModuleResult(raw_data={"company": "Acme"})
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"parsed": True})
        )

        result = await llm_service.parse_module_result(module, raw)

        assert result == {"parsed": True}

    @pytest.mark.asyncio
    async def test_returns_error_dict_if_structured_chat_raises(self, llm_service):
        module = MockModule()
        raw = SearchModuleResult(raw_data={"company": "Acme"})
        llm_service._client.chat.completions.create = AsyncMock(
            side_effect=_connection_error()
        )

        result = await llm_service.parse_module_result(module, raw)

        assert "error" in result
        assert "LLM parsing failed" in result["error"]


class TestSynthesizeResults:
    def _make_result(self, status=ModuleStatus.COMPLETED):
        return SearchResult(
            module_id="mod",
            module_name="Mod",
            status=status,
            data={"findings": []},
        )

    @pytest.mark.asyncio
    async def test_score_below_30_maps_to_low(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"risk_score": 10, "summary": "Low risk."})
        )

        result = await llm_service.synthesize_results("Acme", "123", "GB", [self._make_result()])

        assert result.overall_risk_level == "low"
        assert result.risk_score == 10

    @pytest.mark.asyncio
    async def test_score_30_to_59_maps_to_medium(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"risk_score": 45, "summary": "Medium risk."})
        )

        result = await llm_service.synthesize_results("Acme", "123", "GB", [self._make_result()])

        assert result.overall_risk_level == "medium"
        assert result.risk_score == 45

    @pytest.mark.asyncio
    async def test_score_60_and_above_maps_to_high(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"risk_score": 75, "summary": "High risk."})
        )

        result = await llm_service.synthesize_results("Acme", "123", "GB", [self._make_result()])

        assert result.overall_risk_level == "high"
        assert result.risk_score == 75

    @pytest.mark.asyncio
    async def test_returns_risk_summary_with_correct_fields(self, llm_service):
        llm_service._client.chat.completions.create = AsyncMock(
            return_value=_mock_response({"risk_score": 20, "summary": "Looks clean."})
        )

        result = await llm_service.synthesize_results("Acme", "123", "GB", [self._make_result()])

        assert result.summary == "Looks clean."
        assert result.overall_risk_level == "low"
        assert result.risk_score == 20
