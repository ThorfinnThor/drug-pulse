import { useState, useRef, useEffect } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EntityBadge } from "./EntityBadge";
import { searchAllEntities } from "@/data/mockData";

export const SearchBar = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length > 1) {
      const searchResults = searchAllEntities(query);
      setResults(searchResults);
      setShowResults(true);
    } else {
      setResults([]);
      setShowResults(false);
    }
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleResultClick = (result: any) => {
    setQuery(result.name);
    setShowResults(false);
    // Navigate to the entity page
    console.log(`Navigate to ${result.type} with id ${result.id}`);
  };

  return (
    <div ref={searchRef} className="relative w-full max-w-sm">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search companies, drugs, trials..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 pr-4"
          onFocus={() => query.length > 1 && setShowResults(true)}
        />
      </div>

      {showResults && results.length > 0 && (
        <Card className="absolute top-full left-0 right-0 mt-1 z-50 max-h-96 overflow-y-auto">
          <div className="p-2">
            {results.map((result, index) => (
              <Button
                key={`${result.type}-${result.id}`}
                variant="ghost"
                className="w-full justify-start h-auto p-3 mb-1"
                onClick={() => handleResultClick(result)}
              >
                <div className="flex items-center space-x-3 w-full">
                  <EntityBadge type={result.type} />
                  <div className="flex-1 text-left">
                    <div className="font-medium">{result.name}</div>
                    {result.subtitle && (
                      <div className="text-sm text-muted-foreground">{result.subtitle}</div>
                    )}
                  </div>
                </div>
              </Button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};