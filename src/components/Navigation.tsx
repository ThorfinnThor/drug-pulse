import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { SearchBar } from "./SearchBar";
import { User, Settings, LogOut, Shield, FlaskConical } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";

export const Navigation = () => {
  const [user, setUser] = useState<any>(null);
  const [isOwner, setIsOwner] = useState(false);

  useEffect(() => {
    // Get initial session
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user || null);
      
      if (session?.user) {
        checkOwnerRole(session.user.id);
      }
    };

    getSession();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
      
      if (session?.user) {
        checkOwnerRole(session.user.id);
      } else {
        setIsOwner(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const checkOwnerRole = async (userId: string) => {
    try {
      const { data: roles } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', userId)
        .eq('role', 'owner');
      
      setIsOwner(roles && roles.length > 0);
    } catch (error) {
      console.error('Error checking owner role:', error);
      setIsOwner(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="flex items-center justify-between w-full max-w-6xl mx-auto px-4 h-16">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <FlaskConical className="h-4 w-4 text-white" />
            </div>
            <h1 className="text-xl font-bold text-primary">PharmaIntel</h1>
            <Badge variant="secondary" className="text-xs">Beta</Badge>
          </Link>
          
          <nav className="hidden md:flex items-center gap-6">
            <Link to="/" className="text-sm font-medium hover:text-primary transition-colors">
              Home
            </Link>
            {isOwner && (
              <Link to="/admin" className="text-sm font-medium hover:text-primary transition-colors flex items-center gap-1">
                <Shield className="h-3 w-3" />
                Admin
              </Link>
            )}
          </nav>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="w-96">
            <SearchBar />
          </div>
          
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">{user.email}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {isOwner && (
                  <DropdownMenuItem asChild>
                    <Link to="/admin" className="flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      Admin Dashboard
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={handleSignOut} className="text-red-600">
                  <LogOut className="h-4 w-4 mr-2" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild size="sm">
              <Link to="/auth">Sign In</Link>
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
};