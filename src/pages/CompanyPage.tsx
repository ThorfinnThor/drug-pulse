import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EntityBadge } from "@/components/EntityBadge";
import { Navigation } from "@/components/Navigation";
import { Building2, TrendingUp, Calendar, DollarSign, FileText, ExternalLink, Globe } from "lucide-react";
import { mockCompanies, type Company } from "@/data/mockData";

export const CompanyPage = ({ companyId }: { companyId: number }) => {
  const [company, setCompany] = useState<Company | null>(null);

  useEffect(() => {
    const foundCompany = mockCompanies.find(c => c.id === companyId);
    setCompany(foundCompany || null);
  }, [companyId]);

  if (!company) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="container mx-auto py-8 px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Company not found</h1>
          </div>
        </div>
      </div>
    );
  }

  const formatMarketCap = (value: number) => {
    return `$${(value / 1000000000).toFixed(1)}B`;
  };

  const mockPipeline = [
    { phase: 'Discovery', count: 15, description: 'Early research assets' },
    { phase: 'Phase 1', count: 12, description: 'First-in-human studies' },
    { phase: 'Phase 2', count: 8, description: 'Proof of concept' },
    { phase: 'Phase 3', count: 5, description: 'Pivotal trials' },
    { phase: 'Approved', count: 3, description: 'Commercial products' }
  ];

  const mockReadouts = [
    {
      asset: 'Asset A',
      indication: 'Oncology',
      phase: 'Phase 3',
      date: '2024-09-15',
      catalyst: 'Primary endpoint readout'
    },
    {
      asset: 'Asset B', 
      indication: 'Immunology',
      phase: 'Phase 2',
      date: '2024-11-30',
      catalyst: 'Interim analysis'
    },
    {
      asset: 'Asset C',
      indication: 'Neurology',
      phase: 'Phase 3',
      date: '2025-02-28',
      catalyst: 'Final analysis'
    }
  ];

  const mockFilings = [
    {
      type: '10-K',
      date: '2024-02-15',
      title: 'Annual Report 2023',
      url: '#'
    },
    {
      type: '10-Q',
      date: '2024-01-20',
      title: 'Quarterly Report Q4 2023',
      url: '#'
    },
    {
      type: '8-K',
      date: '2024-01-15',
      title: 'Clinical Trial Results Announcement',
      url: '#'
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      
      <div className="container mx-auto py-8 px-4 space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <EntityBadge type="company" size="lg" />
            <div className="flex-1">
              <div className="flex items-center gap-4">
                <h1 className="text-3xl font-bold">{company.name}</h1>
                {company.ticker && (
                  <Badge variant="outline" className="text-lg px-3 py-1">
                    {company.ticker}
                  </Badge>
                )}
              </div>
              <p className="text-lg text-muted-foreground mt-1">{company.description}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-6 text-sm">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-pharma-blue" />
              <span className="font-medium">Location:</span>
              <span>{company.country}</span>
            </div>
            {company.marketCap && (
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-pharma-green" />
                <span className="font-medium">Market Cap:</span>
                <span>{formatMarketCap(company.marketCap)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Pipeline Assets</p>
                  <p className="text-2xl font-bold text-pharma-blue">{company.pipelineAssets}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-pharma-blue/60" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Upcoming Readouts</p>
                  <p className="text-2xl font-bold text-pharma-orange">{company.upcomingReadouts}</p>
                </div>
                <Calendar className="h-8 w-8 text-pharma-orange/60" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Latest Filing</p>
                  <p className="text-2xl font-bold text-pharma-green">
                    {company.latestFiling ? new Date(company.latestFiling).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
                <FileText className="h-8 w-8 text-pharma-green/60" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pipeline Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Pipeline Summary
            </CardTitle>
            <CardDescription>
              Asset distribution by development phase
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockPipeline.map((phase, index) => (
                <div key={phase.phase} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-primary flex items-center justify-center text-white font-bold">
                      {phase.count}
                    </div>
                    <div>
                      <h4 className="font-semibold">{phase.phase}</h4>
                      <p className="text-sm text-muted-foreground">{phase.description}</p>
                    </div>
                  </div>
                  <div className="w-32 bg-muted rounded-full h-2">
                    <div 
                      className="h-2 bg-gradient-primary rounded-full"
                      style={{ width: `${(phase.count / 15) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Upcoming Readouts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Upcoming Readouts
            </CardTitle>
            <CardDescription>
              Key clinical milestones in the next 12 months
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockReadouts.map((readout, index) => (
                <div key={index} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <h4 className="font-semibold">{readout.asset}</h4>
                        <Badge variant="outline" className="bg-pharma-orange/10 text-pharma-orange border-pharma-orange/20">
                          {readout.phase}
                        </Badge>
                      </div>
                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <span><strong>Indication:</strong> {readout.indication}</span>
                        <span><strong>Date:</strong> {new Date(readout.date).toLocaleDateString()}</span>
                      </div>
                      <p className="text-sm">{readout.catalyst}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Latest Filings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Recent SEC Filings
            </CardTitle>
            <CardDescription>
              Latest regulatory filings and disclosures
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockFilings.map((filing, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <Badge variant="outline">{filing.type}</Badge>
                    <div>
                      <h4 className="font-medium">{filing.title}</h4>
                      <p className="text-sm text-muted-foreground">{new Date(filing.date).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Filing
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};