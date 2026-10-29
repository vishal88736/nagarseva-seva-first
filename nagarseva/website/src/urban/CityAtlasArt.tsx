import { Building2, Droplets, House, MapPinned, Route, ShieldCheck } from 'lucide-react'

/** Decorative civic medallions, echoing the supplied reference's floating discs. */
export default function CityAtlasArt() {
  const discs = [
    { Icon: Building2, name: 'buildings', color: 'lavender', x: 153, y: -26, size: 111, tilt: -23 },
    { Icon: House, name: 'housing', color: 'amber', x: 239, y: -43, size: 108, tilt: 19 },
    { Icon: MapPinned, name: 'map', color: 'teal', x: 315, y: 9, size: 100, tilt: 29 },
    { Icon: Droplets, name: 'water', color: 'blue', x: 101, y: 89, size: 110, tilt: -18 },
    { Icon: Route, name: 'access', color: 'mint', x: 333, y: 112, size: 103, tilt: -22 },
    { Icon: ShieldCheck, name: 'review', color: 'violet', x: 235, y: 175, size: 110, tilt: 22 },
    { Icon: House, name: 'homes', color: 'gold', x: 152, y: 208, size: 96, tilt: -27 },
  ]
  return <div className="city-atlas-art" aria-hidden="true">
    <div className="atlas-orbit" />
    {discs.map(({ Icon, name, color, x, y, size, tilt }) => <div key={name} className={`atlas-disc ${color}`} style={{ left: x, top: y, width: size, height: size, transform: `rotate(${tilt}deg) rotateY(-20deg)` }}><div className="atlas-disc-face"><Icon strokeWidth={1.3} /></div></div>)}
    <i className="atlas-star one" /><i className="atlas-star two" /><i className="atlas-star three" />
  </div>
}
