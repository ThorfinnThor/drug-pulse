import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EntityBadge } from "@/components/EntityBadge";
import { Navigation } from "@/components/Navigation";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp, Users, DollarSign, Calendar, ExternalLink } from "lucide-react";
import { mockIndications, type Indication } from "@/data/mockData";

export const IndicationPage = ({ indicationId }: { indicationId: number }) => {
  const [indication, setIndication] = useState<Indication | null>(null);

  useEffect(() => {
    const foundIndication = mockIndications.find(i => i.id === indicationId);
    setIndication(foundIndication || null);
  }, [indicationId]);

  if (!indication) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="container mx-auto py-8 px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Indication not found</h1>
          </div>
        </div>
      </div>
    );
  }

  const funnelData = [
    { phase: 'Phase 1', trials: indication.trialsCount.phase1, fill: 'hsl(var(--pharma-blue))' },
    { phase: 'Phase 2', trials: indication.trialsCount.phase2, fill: 'hsl(var(--pharma-green))' },
    { phase: 'Phase 3', trials: indication.trialsCount.phase3, fill: 'hsl(var(--pharma-orange))' },
    { phase: 'Phase 4', trials: indication.trialsCount.phase4, fill: 'hsl(var(--pharma-purple))' }
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      
      <div className="container mx-auto py-8 px-4 space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <EntityBadge type="indication" size="lg" />
            <div>
              <h1 className="text-3xl font-bold">{indication.name}</h1>
              <p className="text-lg text-muted-foreground mt-1">{indication.description}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-pharma-blue" />
              <span className="font-medium">Prevalence:</span>
              <span>{indication.prevalence}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-pharma-green" />
              <span className="font-medium">Market Size:</span>
              <span>{indication.marketSize}</span>
            </div>
          </div>
        </div>

        {/* Trial Funnel Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Clinical Trial Funnel
            </CardTitle>
            <CardDescription>
              Active trials by development phase
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="phase" 
                    tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <YAxis 
                    tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                      boxShadow: 'var(--shadow-md)'
                    }}
                  />
                  <Bar dataKey="trials" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Late Stage Trials */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Late-Stage Trials
            </CardTitle>
            <CardDescription>
              Phase 2/3 trials with upcoming readouts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {indication.lateStageTrials.map((trial) => (
                <div key={trial.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="bg-pharma-orange/10 text-pharma-orange border-pharma-orange/20">
                          Phase {trial.phase}
                        </Badge>
                        <Badge variant="outline" className={
                          trial.status === 'Recruiting' 
                            ? 'bg-pharma-green/10 text-pharma-green border-pharma-green/20'
                            : 'bg-muted text-muted-foreground'
                        }>
                          {trial.status}
                        </Badge>
                      </div>
                      <h4 className="font-semibold">{trial.title}</h4>
                      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                        <span><strong>Sponsor:</strong> {trial.sponsor}</span>
                        <span><strong>Enrollment:</strong> {trial.enrollment.toLocaleString()}</span>
                        <span><strong>Sites:</strong> {trial.sites}</span>
                        <span><strong>Completion:</strong> {new Date(trial.completionDate).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" className="ml-4">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Trial
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};