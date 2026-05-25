import CompaniesHouseView from './modules/CompaniesHouseView'
import ICIJLeaksView from './modules/ICIJLeaksView'
import AdverseMediaView from './modules/AdverseMediaView'

export { CompaniesHouseView, ICIJLeaksView, AdverseMediaView }

export function ModuleView({ moduleId, data }: { moduleId: string; data: unknown }) {
  if (moduleId === 'companies_house') return <CompaniesHouseView data={data} />
  if (moduleId === 'adverse_media') return <AdverseMediaView data={data} />
  if (moduleId === 'icij_offshore_leaks') return <ICIJLeaksView data={data} />
  return <pre className="json-viewer">{JSON.stringify(data, null, 2)}</pre>
}
