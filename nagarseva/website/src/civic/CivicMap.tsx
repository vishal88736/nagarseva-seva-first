import {Fragment,useEffect,useMemo,useRef,useState} from 'react'
import {CircleMarker,GeoJSON,MapContainer,Marker,Polyline,ScaleControl,TileLayer,Tooltip,useMap,useMapEvents} from 'react-leaflet'
import L from 'leaflet'
import type {FeatureCollection,Polygon} from 'geojson'
import {t,formatNumber} from '../i18n/locale'
import {useLanguage} from '../i18n/LanguageProvider'
import LocalizedMapControls from '../urban/LocalizedMapControls'
import {cameraIntent,geometrySignature,gridStep,groupPoints} from './mapState'
import type {CameraSnapshot} from './mapState'
import {SourceNote} from './SourceNote'
import type {Settlement} from './types'
import 'leaflet/dist/leaflet.css'

type Selection={rows:Settlement[];selected:string;onSelect:(id:string)=>void}
function MapCamera({rows,selected,request,signature}:{rows:Settlement[];selected:string;request:number;signature:string}) {
 const map=useMap(),previous=useRef<CameraSnapshot|null>(null)
 useEffect(()=>{
  const next={geometry:signature,selected,hasSelection:rows.some(row=>row.id===selected),count:rows.length,fitRequest:request},intent=cameraIntent(previous.current,next)
  previous.current=next
  const focus=intent==='selection'?rows.filter(row=>row.id===selected):rows
  if(intent!=='preserve'&&focus.length){const bounds=L.geoJSON({type:'FeatureCollection',features:focus.map(row=>({type:'Feature',properties:{},geometry:row.geometry}))} as FeatureCollection).getBounds();if(bounds.isValid())map.fitBounds(bounds,{padding:[30,30],maxZoom:intent==='selection'?16:13,animate:false})}
 },[map,rows,selected,request,signature])
 useEffect(()=>{const observer=new ResizeObserver(()=>map.invalidateSize({pan:false}));observer.observe(map.getContainer());return()=>observer.disconnect()},[map])
 return null
}
function ViewportStatus(){
 const map=useMap(),[position,setPosition]=useState(()=>({center:map.getCenter().wrap(),zoom:map.getZoom()}))
 useEffect(()=>setPosition({center:map.getCenter().wrap(),zoom:map.getZoom()}),[map])
 const events=useMemo(()=>({moveend:()=>setPosition({center:map.getCenter().wrap(),zoom:map.getZoom()}),zoomend:()=>setPosition({center:map.getCenter().wrap(),zoom:map.getZoom()})}),[map])
 useMapEvents(events)
 return <output className="map-viewport-status" data-lat={position.center.lat.toFixed(6)} data-lng={position.center.lng.toFixed(6)} data-zoom={position.zoom}><span>{t('d.mapCenter')}: {formatNumber(position.center.lat,4)}°, {formatNumber(position.center.lng,4)}°</span><span>{t('d.mapZoom')} {formatNumber(position.zoom,0)}</span></output>
}
function CoordinateGrid(){
 const map=useMap(),[bounds,setBounds]=useState(()=>map.getBounds())
 useEffect(()=>setBounds(map.getBounds()),[map])
 const events=useMemo(()=>({moveend:()=>setBounds(map.getBounds()),zoomend:()=>setBounds(map.getBounds())}),[map])
 useMapEvents(events)
 const step=gridStep(Math.max(bounds.getNorth()-bounds.getSouth(),bounds.getEast()-bounds.getWest())),lines:[number,number][][]=[]
 for(let latitude=Math.ceil(bounds.getSouth()/step)*step;latitude<bounds.getNorth();latitude+=step)lines.push([[latitude,bounds.getWest()],[latitude,bounds.getEast()]])
 for(let longitude=Math.ceil(bounds.getWest()/step)*step;longitude<bounds.getEast();longitude+=step)lines.push([[bounds.getSouth(),longitude],[bounds.getNorth(),longitude]])
 return <>{lines.map((positions,index)=><Polyline key={index} positions={positions} pathOptions={{color:'#9dbfce',weight:1,opacity:.6}} interactive={false}/>)}</>
}
function LocationTargets({rows,selected,onSelect}:Selection){
 const map=useMap(),{language}=useLanguage(),[zoom,setZoom]=useState(map.getZoom())
 useEffect(()=>setZoom(map.getZoom()),[map])
 const events=useMemo(()=>({zoomend:()=>setZoom(map.getZoom())}),[map])
 useMapEvents(events)
 const groups=useMemo(()=>groupPoints(rows,(latitude,longitude)=>map.project([latitude,longitude],zoom)),[map,rows,zoom])
 if(zoom>12)return null
 return <>{groups.map(group=>group.rows.length>1?<Marker key={`${language}-${group.key}`} position={[group.latitude,group.longitude]} icon={L.divIcon({className:'settlement-cluster',html:`<span>${formatNumber(group.rows.length,0)}</span>`,iconSize:[34,34],iconAnchor:[17,17]})} title={t('d.mapCluster',{count:formatNumber(group.rows.length,0)})} keyboard eventHandlers={{click:()=>map.fitBounds(L.geoJSON({type:'FeatureCollection',features:group.rows.map(row=>({type:'Feature',properties:{},geometry:row.geometry}))} as FeatureCollection).getBounds(),{padding:[45,45],maxZoom:15,animate:false}),add:event=>{(event.target as L.Marker).getElement()?.setAttribute('aria-label',t('d.mapCluster',{count:formatNumber(group.rows.length,0)}))}}}><Tooltip>{t('d.mapCluster',{count:formatNumber(group.rows.length,0)})}</Tooltip></Marker>:<CircleMarker key={group.rows[0].id} center={[group.latitude,group.longitude]} radius={group.rows[0].id===selected?8:5} pathOptions={{className:'settlement-location-target',color:'#fff',weight:2,fillColor:'#008f9d',fillOpacity:1}} eventHandlers={{click:()=>onSelect(group.rows[0].id)}}><Tooltip>{t(group.rows[0].name)}</Tooltip></CircleMarker>)}</>
}
function SettlementLayer({rows,selected,onSelect,signature}:Selection&{signature:string}){
 const {language}=useLanguage(),layer=useRef<L.GeoJSON>(null),handler=useRef(onSelect),selection=useRef(selected)
 handler.current=onSelect;selection.current=selected
 const collection=useMemo<FeatureCollection<Polygon,{id:string;name:string}>>(()=>({type:'FeatureCollection',features:rows.map(row=>({type:'Feature',id:row.id,geometry:row.geometry,properties:{id:row.id,name:row.name}}))}),[rows])
 function style(id:string){return {className:'demo-settlement-polygon',color:id===selection.current?'#004b55':'#008f9d',weight:id===selection.current?4:2,fillColor:id===selection.current?'#12b8ad':'#1bb3c0',fillOpacity:id===selection.current ? .55 : .3}}
 useEffect(()=>{layer.current?.eachLayer(item=>{const path=item as L.Polygon&{feature?:{properties:{id:string;name:string}}},feature=path.feature;if(!feature)return;path.setStyle(style(feature.properties.id));path.getTooltip()?.setContent(t(feature.properties.name));const element=path.getElement() as SVGElement|undefined;element?.classList.toggle('is-selected',feature.properties.id===selected);element?.setAttribute('aria-label',t(feature.properties.name));element?.setAttribute('role','button');element?.setAttribute('tabindex','-1');if(element)element.onkeydown=(event:KeyboardEvent)=>{if(['Enter',' '].includes(event.key)){event.preventDefault();handler.current(feature.properties.id)}}})},[selected,language,signature])
 return <GeoJSON key={signature} ref={layer} data={collection} style={feature=>style(feature?.properties.id||'')} onEachFeature={(feature,item)=>{item.bindTooltip(t(feature.properties.name));item.on('click',()=>handler.current(feature.properties.id));item.on('mouseover',()=>{(item as L.Path).setStyle({fillOpacity:.65})});item.on('mouseout',()=>{(item as L.Path).setStyle({fillOpacity:feature.properties.id===selection.current ? .55 : .3})})}}/>
}
export default function CivicMap({rows,selected='',onSelect,compact=false}:Omit<Selection,'selected'>&{selected?:string;compact?:boolean}){
 useLanguage()
 const [tiles,setTiles]=useState(true),[tileStatus,setTileStatus]=useState<'loading'|'ready'|'unavailable'>('loading'),[tileAttempt,setTileAttempt]=useState(0),[visible,setVisible]=useState(true),[fit,setFit]=useState(0),loaded=useRef(0)
 const signature=useMemo(()=>geometrySignature(rows),[rows]),fallback=!tiles||tileStatus==='unavailable'
 useEffect(()=>{if(!tiles||tileStatus!=='loading')return;const timer=setTimeout(()=>{if(!loaded.current)setTileStatus('unavailable')},8000);return()=>clearTimeout(timer)},[tiles,tileStatus,tileAttempt])
 function retry(){loaded.current=0;setTileStatus('loading');setTileAttempt(attempt=>attempt+1)}
 return <section className={`us-panel workspace-map demo-map ${compact?'demo-map-compact':''}`} aria-label={t('d.mapTitle')}>
  <div className="workspace-map-toolbar"><strong>{t('d.mapTitle')}</strong><button className="us-button" onClick={()=>setFit(value=>value+1)} disabled={!rows.length}>{t('d.fitMap')}</button><label><input type="checkbox" checked={visible} onChange={event=>setVisible(event.target.checked)}/>{t('d.geometryLayer')}</label><label><input type="checkbox" checked={tiles} onChange={event=>{setTiles(event.target.checked);if(event.target.checked)retry()}}/>{t('Online OSM basemap')}</label></div>
  <div className="us-map"><MapContainer center={[19.1,72.88]} zoom={11} minZoom={4} maxZoom={19} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} zoomControl={false} aria-label={t('d.mapTitle')}><LocalizedMapControls label="d.mapTitle"/><MapCamera rows={rows} selected={selected} request={fit} signature={signature}/><ScaleControl position="bottomleft" imperial={false}/>{fallback&&<CoordinateGrid/>}{tiles&&tileStatus!=='unavailable'&&<TileLayer key={tileAttempt} url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} attribution={t('map.attribution')} eventHandlers={{loading:()=>{loaded.current=0;setTileStatus('loading')},tileload:()=>{loaded.current+=1;setTileStatus('ready')},load:()=>setTileStatus(loaded.current?'ready':'unavailable')}}/>}{visible&&<Fragment><SettlementLayer rows={rows} selected={selected} onSelect={onSelect} signature={signature}/><LocationTargets rows={rows} selected={selected} onSelect={onSelect}/></Fragment>}<ViewportStatus/></MapContainer></div>
  <div className="settlement-map-legend"><span><i/>{t('d.geometryLayer')}</span><span><i className="selected"/>{t('d.mapSelected')}</span>{fallback?<span className="map-fallback-label">{t('d.mapOffline')}</span>:tileStatus==='loading'?<span role="status">{t('d.mapLoading')}</span>:null}</div>
  <p className="map-group-help">{t('d.mapLayerHelp')}</p>
  {tiles&&tileStatus==='unavailable'&&<div className="map-tile-error" role="status"><span>{t('d.mapTileError')}</span><button className="us-button" onClick={retry}>{t('d.mapRetry')}</button></div>}
  <SourceNote/><p className="demo-map-notice">{t('d.mapNotice')}</p>{!rows.length&&<p className="map-no-results" role="status">{t('d.noMatches')}</p>}
 </section>
}
