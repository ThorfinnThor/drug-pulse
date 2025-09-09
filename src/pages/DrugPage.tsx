import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EntityBadge } from "@/components/EntityBadge";
import { Navigation } from "@/components/Navigation";
import { RNPVCalculator } from "@/components/rNPVCalculator";
import { Pill, Building2, Target, TrendingUp, Users, ExternalLink } from "lucide-react";
import { mockDrugs, type Drug } from "@/data/mockData";

export const DrugPage = ({ drugId }: { drugId: number }) => {
  const [drug, setDrug] = useState<Drug | null>(null);

  useEffect(() => {
    const foundDrug = mockDrugs.find(d => d.id === drugId);
    setDrug(foundDrug || null);
  }, [drugId]);

  if (!drug) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="container mx-auto py-8 px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Drug not found</h1>
          </div>
        </div>
      </div>
    );
  }

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'Approved': return 'bg-pharma-green/10 text-pharma-green border-pharma-green/20';
      case 'Phase 3': return 'bg-pharma-orange/10 text-pharma-orange border-pharma-orange/20';
      case 'Phase 2': return 'bg-pharma-blue/10 text-pharma-blue border-pharma-blue/20';
      case 'Phase 1': return 'bg-pharma-purple/10 text-pharma-purple border-pharma-purple/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      
      <div className="container mx-auto py-8 px-4 space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <EntityBadge type="drug" size="lg" />
            <div>
              <h1 className="text-3xl font-bold">{drug.name}</h1>
              <div className="flex items-center gap-4 mt-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Building2 className="h-4 w-4" />
                  <span>{drug.company}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Target className="h-4 w-4" />
                  <span>{drug.mechanism}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Badge variant="outline" className={getPhaseColor(drug.phase)}>
              {drug.phase}
            </Badge>
            <Badge variant="outline" className="bg-muted text-muted-foreground">
              {drug.status}
            </Badge>
            {drug.indications.map((indication, index) => (
              <Badge key={index} variant="secondary">
                {indication}
              </Badge>
            ))}
          </div>

          {drug.nextMilestone && (
            <div className="flex items-center gap-2 text-sm text-pharma-orange">
              <TrendingUp className="h-4 w-4" />
              <span><strong>Next Milestone:</strong> {drug.nextMilestone}</span>
            </div>
          )}
        </div>

        {/* Competitive Landscape */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Competitive Landscape
            </CardTitle>
            <CardDescription>
              Other assets targeting the same indications
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Current Drug */}
              <div className="border-2 border-primary/20 rounded-lg p-4 bg-primary/5">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <h4 className="font-semibold text-primary">{drug.name} (Current)</h4>
                      <Badge variant="outline" className={getPhaseColor(drug.phase)}>
                        {drug.phase}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Building2 className="h-4 w-4" />
                      <span>{drug.company}</span>
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Details
                  </Button>
                </div>
              </div>

              {/* Competitors */}
              {drug.competitors.map((competitor, index) => (
                <div key={index} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <h4 className="font-semibold">{competitor.name}</h4>
                        <Badge variant="outline" className={getPhaseColor(competitor.phase)}>
                          {competitor.phase}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Building2 className="h-4 w-4" />
                        <span>{competitor.company}</span>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Compare
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* rNPV Calculator */}
        <div>
          <div className="mb-6">
            <h2 className="text-2xl font-bold mb-2">Market Valuation</h2>
            <p className="text-muted-foreground">
              Estimate the risk-adjusted net present value based on market assumptions
            </p>
          </div>
          <RNPVCalculator />
        </div>
      </div>
    </div>
  );
};