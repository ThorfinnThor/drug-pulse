import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navigation } from "@/components/Navigation";
import { EntityBadge } from "@/components/EntityBadge";
import { SearchBar } from "@/components/SearchBar";
import { FlaskConical, TrendingUp, Building2, Pill, ArrowRight, Users, DollarSign } from "lucide-react";
import { mockCompanies, mockDrugs, mockIndications } from "@/data/mockData";

const Index = () => {
  const featuredCompanies = mockCompanies.slice(0, 3);
  const featuredDrugs = mockDrugs.slice(0, 3);
  const featuredIndications = mockIndications.slice(0, 3);

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      
      {/* Hero Section */}
      <section className="relative py-20 px-4 bg-gradient-hero">
        <div className="absolute inset-0 bg-gradient-to-b from-background/5 to-background/20" />
        <div className="container relative mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-4xl md:text-6xl font-bold text-white">
              Pharma Strategy
              <span className="block bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                Intelligence
              </span>
            </h1>
            <p className="text-xl text-white/90 max-w-2xl mx-auto">
              Aggregate clinical trials, drug pipelines, and market intelligence 
              for strategic decision making in life sciences.
            </p>
          </div>
          
          <div className="max-w-lg mx-auto">
            <SearchBar />
          </div>
          
          <div className="flex flex-wrap justify-center gap-4 pt-4">
            <Badge variant="secondary" className="bg-white/10 text-white border-white/20">
              280K+ Clinical Trials
            </Badge>
            <Badge variant="secondary" className="bg-white/10 text-white border-white/20">
              15K+ Drug Assets
            </Badge>
            <Badge variant="secondary" className="bg-white/10 text-white border-white/20">
              5K+ Companies
            </Badge>
          </div>
        </div>
      </section>

      {/* Featured Companies */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold mb-2">Featured Companies</h2>
              <p className="text-muted-foreground">Leading pharmaceutical and biotech companies</p>
            </div>
            <Button variant="outline">
              View All Companies
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6">
            {featuredCompanies.map((company) => (
              <Card key={company.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <EntityBadge type="company" />
                    {company.ticker && (
                      <Badge variant="outline">{company.ticker}</Badge>
                    )}
                  </div>
                  <CardTitle className="text-xl">{company.name}</CardTitle>
                  <CardDescription>{company.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-pharma-blue" />
                      <span>{company.pipelineAssets} Assets</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FlaskConical className="h-4 w-4 text-pharma-orange" />
                      <span>{company.upcomingReadouts} Readouts</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <span>{company.country}</span>
                    </div>
                    {company.marketCap && (
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-pharma-green" />
                        <span>${(company.marketCap / 1000000000).toFixed(1)}B</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Drugs */}
      <section className="py-16 px-4 bg-muted/30">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold mb-2">Featured Assets</h2>
              <p className="text-muted-foreground">Promising drug candidates across therapeutic areas</p>
            </div>
            <Button variant="outline">
              View All Drugs
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6">
            {featuredDrugs.map((drug) => (
              <Card key={drug.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <EntityBadge type="drug" />
                    <Badge variant="outline" className={
                      drug.phase === 'Approved' 
                        ? 'bg-pharma-green/10 text-pharma-green border-pharma-green/20'
                        : 'bg-pharma-orange/10 text-pharma-orange border-pharma-orange/20'
                    }>
                      {drug.phase}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl">{drug.name}</CardTitle>
                  <CardDescription>{drug.mechanism}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <span>{drug.company}</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {drug.indications.slice(0, 2).map((indication, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {indication}
                        </Badge>
                      ))}
                      {drug.indications.length > 2 && (
                        <Badge variant="secondary" className="text-xs">
                          +{drug.indications.length - 2} more
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Indications */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold mb-2">Key Therapeutic Areas</h2>
              <p className="text-muted-foreground">High-value indications with active development</p>
            </div>
            <Button variant="outline">
              View All Indications
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6">
            {featuredIndications.map((indication) => (
              <Card key={indication.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <EntityBadge type="indication" />
                  <CardTitle className="text-xl">{indication.name}</CardTitle>
                  <CardDescription>{indication.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-pharma-blue" />
                        <span>Prevalence</span>
                      </div>
                      <span className="font-medium">{indication.prevalence}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-pharma-green" />
                        <span>Market Size</span>
                      </div>
                      <span className="font-medium">{indication.marketSize}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <FlaskConical className="h-4 w-4 text-pharma-orange" />
                        <span>Active Trials</span>
                      </div>
                      <span className="font-medium">
                        {Object.values(indication.trialsCount).reduce((a, b) => a + b, 0)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12 px-4 bg-muted/30">
        <div className="container mx-auto text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="h-6 w-6 rounded bg-gradient-primary flex items-center justify-center">
              <FlaskConical className="h-3 w-3 text-white" />
            </div>
            <span className="text-lg font-bold">PharmaIntel</span>
          </div>
          <p className="text-muted-foreground">
            Aggregating public life sciences data for strategic intelligence
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
