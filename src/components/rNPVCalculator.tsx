import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Calculator, DollarSign, TrendingUp } from "lucide-react";

interface NPVInputs {
  patients: number;
  treatmentRate: number;
  pricePerYear: number;
  durationYears: number;
  pos: number;
  wacc: number;
  competitionFactor: number;
  yearsToLaunch: number;
}

export const RNPVCalculator = () => {
  const [inputs, setInputs] = useState<NPVInputs>({
    patients: 25000,
    treatmentRate: 0.35,
    pricePerYear: 120000,
    durationYears: 2.0,
    pos: 0.55,
    wacc: 0.12, 
    competitionFactor: 0.65,
    yearsToLaunch: 2
  });

  const calculateNPV = () => {
    const peakSales = inputs.patients * inputs.treatmentRate * inputs.pricePerYear * 
                     inputs.durationYears * inputs.competitionFactor;
    const rnpv = peakSales * inputs.pos / Math.pow(1 + inputs.wacc, inputs.yearsToLaunch);
    
    return {
      peakSales: peakSales / 1000000, // Convert to millions
      rnpv: rnpv / 1000000, // Convert to millions
      patientValue: inputs.pricePerYear * inputs.durationYears,
      treatablePopulation: inputs.patients * inputs.treatmentRate
    };
  };

  const results = calculateNPV();

  const updateInput = (key: keyof NPVInputs, value: number) => {
    setInputs(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calculator className="h-5 w-5" />
            rNPV Calculator
          </CardTitle>
          <CardDescription>
            Adjust assumptions to estimate risk-adjusted net present value
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Market Size Inputs */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-muted-foreground">Market Parameters</h4>
            
            <div className="space-y-2">
              <Label htmlFor="patients">Total Patient Population</Label>
              <div className="flex items-center space-x-2">
                <Input
                  id="patients"
                  type="number"
                  value={inputs.patients}
                  onChange={(e) => updateInput('patients', parseInt(e.target.value) || 0)}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground">patients</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Treatment Rate: {(inputs.treatmentRate * 100).toFixed(0)}%</Label>
              <Slider
                value={[inputs.treatmentRate]}
                onValueChange={([value]) => updateInput('treatmentRate', value)}
                max={1}
                min={0.1}
                step={0.05}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="price">Annual Price (USD)</Label>
              <Input
                id="price"
                type="number"
                value={inputs.pricePerYear}
                onChange={(e) => updateInput('pricePerYear', parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label>Treatment Duration: {inputs.durationYears} years</Label>
              <Slider
                value={[inputs.durationYears]}
                onValueChange={([value]) => updateInput('durationYears', value)}
                max={5}
                min={0.5}
                step={0.5}
                className="w-full"
              />
            </div>
          </div>

          {/* Risk Inputs */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-muted-foreground">Risk & Competition</h4>
            
            <div className="space-y-2">
              <Label>Probability of Success: {(inputs.pos * 100).toFixed(0)}%</Label>
              <Slider
                value={[inputs.pos]}
                onValueChange={([value]) => updateInput('pos', value)}
                max={1}
                min={0.1}
                step={0.05}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>Competition Factor: {(inputs.competitionFactor * 100).toFixed(0)}%</Label>
              <Slider
                value={[inputs.competitionFactor]}
                onValueChange={([value]) => updateInput('competitionFactor', value)}
                max={1}
                min={0.2}
                step={0.05}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>WACC: {(inputs.wacc * 100).toFixed(0)}%</Label>
              <Slider
                value={[inputs.wacc]}
                onValueChange={([value]) => updateInput('wacc', value)}
                max={0.25}
                min={0.08}
                step={0.01}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>Years to Launch: {inputs.yearsToLaunch}</Label>
              <Slider
                value={[inputs.yearsToLaunch]}
                onValueChange={([value]) => updateInput('yearsToLaunch', value)}
                max={8}
                min={1}
                step={1}
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Valuation Results
          </CardTitle>
          <CardDescription>
            Calculated based on your assumptions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground">Peak Sales</div>
              <div className="text-2xl font-bold text-pharma-green">
                ${results.peakSales.toFixed(0)}M
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground">rNPV</div>
              <div className="text-2xl font-bold text-primary">
                ${results.rnpv.toFixed(0)}M
              </div>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t">
            <h4 className="text-sm font-semibold">Key Metrics</h4>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Treatable Population</span>
                <Badge variant="outline">{results.treatablePopulation.toLocaleString()} patients</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Patient Value</span>
                <Badge variant="outline">${results.patientValue.toLocaleString()}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Risk-Adjusted Return</span>
                <Badge variant="outline" className="text-pharma-green">
                  {((results.rnpv / (inputs.patients * inputs.pricePerYear / 1000000)) * 100).toFixed(1)}%
                </Badge>
              </div>
            </div>
          </div>

          <div className="text-xs text-muted-foreground mt-4 p-3 bg-muted/50 rounded-lg">
            <strong>Calculation:</strong> Peak Sales = Patients × Treatment Rate × Price × Duration × Competition Factor. 
            rNPV = Peak Sales × POS / (1 + WACC)^Years to Launch
          </div>
        </CardContent>
      </Card>
    </div>
  );
};