import { Search, Building2, Pill, FlaskConical, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { SearchBar } from "./SearchBar";

export const Navigation = () => {
  const [showSearch, setShowSearch] = useState(false);

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <FlaskConical className="h-4 w-4 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-primary bg-clip-text text-transparent">
              PharmaIntel
            </span>
          </div>
          
          <div className="hidden md:flex items-center space-x-1">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              <Building2 className="h-4 w-4 mr-2" />
              Companies
            </Button>
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              <Pill className="h-4 w-4 mr-2" />
              Drugs
            </Button>
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              <FlaskConical className="h-4 w-4 mr-2" />
              Trials
            </Button>
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              <TrendingUp className="h-4 w-4 mr-2" />
              Markets
            </Button>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="hidden md:block">
            <SearchBar />
          </div>
          <Button
            variant="outline"
            size="sm" 
            className="md:hidden"
            onClick={() => setShowSearch(!showSearch)}
          >
            <Search className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {showSearch && (
        <div className="border-t bg-card p-4 md:hidden">
          <SearchBar />
        </div>
      )}
    </nav>
  );
};