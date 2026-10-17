# Indicator contract before real scoring

The default weights and the 60/100 high-priority cutoff are design assumptions. The current app uses authored normalized fixture indices. None is a measured M-East statistic. A higher index means a larger deficit.

For a real trial, approve the raw metric, denominator, geography, period, uncertainty and transformation **before** looking at ranks. Store raw observations alongside the derived index and version the transformation. Never infer poverty, structural safety, tenure or legal eligibility from imagery or an amenity map.

| Input | Candidate observation | Required approval / limitation |
|---|---|---|
| Water | Observed supply hours over a full, documented period | Target hours must be defined by the competent service owner. A possible explicit deficit is `100 × max(0, 1 - observed/target)` for a positive target. This is a candidate formula, not an official standard. Spot checks cannot populate it. |
| Sanitation / drainage | Separately measured functionality/capacity and blockage indicators | Combining unlike measures needs a documented rubric and denominators. Leave the combined score missing until approved. |
| Housing | Qualified assessment of agreed housing-condition indicators | No engineering assessment acquired. Keep missing rather than infer from a polygon or roof. |
| Amenity access | Permitted entrances, accessible walking network, operating hours and affordability | A mapped line is not a traversable route. Define relevant destinations and an approved deficit transform. |
| Risk | Applicable dated authoritative hazard layer and exposure definition | No approved risk layer acquired. Map proximity alone does not create a risk score. |

A missing positive-weight indicator prevents a precise composite score and rank. The displayed interval describes possible contributions, not confidence probability. If the agreed task is only water inspection, the owner may explicitly choose water-only weights, but the report must say it is a water inspection priority, not a general redevelopment ranking. Never tune weights after seeing labels solely to improve agreement.

The trial must distinguish an urgent service defect from whether redevelopment is legally, financially or socially feasible. Neither the weighted score nor the high-priority flag authorises construction, beneficiary allocation or relocation.
