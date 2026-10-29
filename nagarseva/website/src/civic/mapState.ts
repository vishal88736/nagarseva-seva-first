import type {Settlement} from './types.ts'
export type CameraSnapshot={geometry:string;selected:string;hasSelection:boolean;count:number;fitRequest:number}
/** Only spatial/filter/selection changes may move the camera; labels and record edits may not. */
export function cameraIntent(previous:CameraSnapshot|null,next:CameraSnapshot):'data'|'selection'|'preserve' {
 if(!next.count)return 'preserve'
 if(previous&&previous.fitRequest!==next.fitRequest)return 'data'
 if(!previous)return next.hasSelection?'selection':'data'
 if(previous.selected!==next.selected&&next.hasSelection)return 'selection'
 if(previous.geometry!==next.geometry)return 'data'
 return 'preserve'
}
export function geometrySignature(rows:Pick<Settlement,'id'|'geometry'>[]):string {
 return JSON.stringify([...rows].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0).map(row=>[row.id,row.geometry]))
}
export type MapPoint={id:string;latitude:number;longitude:number}
export type PointGroup<T>={key:string;rows:T[];latitude:number;longitude:number}
/** Screen-space grouping is a view calculation; source geometries and identifiers remain unchanged. */
export function groupPoints<T extends MapPoint>(rows:T[],project:(latitude:number,longitude:number)=>{x:number;y:number},cellSize=44):PointGroup<T>[] {
 const cells=new Map<string,T[]>()
 for(const row of rows){const point=project(row.latitude,row.longitude),key=`${Math.floor(point.x/cellSize)}:${Math.floor(point.y/cellSize)}`;cells.set(key,[...(cells.get(key)||[]),row])}
 return [...cells.entries()].map(([key,items])=>({key,rows:items,latitude:items.reduce((sum,row)=>sum+row.latitude,0)/items.length,longitude:items.reduce((sum,row)=>sum+row.longitude,0)/items.length}))
}
export function gridStep(span:number):number {
 if(!Number.isFinite(span)||span<=0)return 1
 const scale=10**Math.floor(Math.log10(span/5)),fraction=span/5/scale
 return (fraction<=1?1:fraction<=2?2:fraction<=5?5:10)*scale
}
