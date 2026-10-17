export type HouseholdOption = {
  id: string; rent_emi: number; maintenance: number; utilities: number; transport: number;
  income_loss: number; temporary_rent: number; temporary_months: number; moving_cost: number
}
export function householdCosts(option: HouseholdOption, income: number, thresholdPct: number) {
  const monthly = option.rent_emi + option.maintenance + option.utilities + option.transport + option.income_loss
  return { monthly_burden_inr: monthly, burden_pct: income > 0 ? monthly / income * 100 : null,
    remaining_income_inr: income - monthly, transition_cost_inr: option.temporary_rent * option.temporary_months + option.moving_cost,
    exceeds_planning_limit: income > 0 ? monthly / income * 100 > thresholdPct : null }
}
export const initialHouseholdOptions: HouseholdOption[] = [
  { id: 'currentHome', rent_emi: 2500, maintenance: 0, utilities: 900, transport: 1000, income_loss: 0, temporary_rent: 0, temporary_months: 0, moving_cost: 0 },
  { id: 'upgrading', rent_emi: 2500, maintenance: 300, utilities: 800, transport: 1000, income_loss: 0, temporary_rent: 0, temporary_months: 0, moving_cost: 1000 },
  { id: 'inSitu', rent_emi: 0, maintenance: 1800, utilities: 1000, transport: 1000, income_loss: 0, temporary_rent: 6000, temporary_months: 24, moving_cost: 10000 },
  { id: 'relocation', rent_emi: 0, maintenance: 1500, utilities: 1000, transport: 2800, income_loss: 2500, temporary_rent: 5000, temporary_months: 12, moving_cost: 15000 },
  { id: 'rentalHousing', rent_emi: 5000, maintenance: 700, utilities: 900, transport: 1400, income_loss: 0, temporary_rent: 0, temporary_months: 0, moving_cost: 5000 },
]
