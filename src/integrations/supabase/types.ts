export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  public: {
    Tables: {
      approvals: {
        Row: {
          agency: string | null
          application_number: string | null
          approval_date: string | null
          created_at: string | null
          document_url: string | null
          drug_id: number | null
          id: number
          indication_id: number | null
        }
        Insert: {
          agency?: string | null
          application_number?: string | null
          approval_date?: string | null
          created_at?: string | null
          document_url?: string | null
          drug_id?: number | null
          id?: number
          indication_id?: number | null
        }
        Update: {
          agency?: string | null
          application_number?: string | null
          approval_date?: string | null
          created_at?: string | null
          document_url?: string | null
          drug_id?: number | null
          id?: number
          indication_id?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "approvals_drug_id_fkey"
            columns: ["drug_id"]
            isOneToOne: false
            referencedRelation: "drugs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "approvals_indication_id_fkey"
            columns: ["indication_id"]
            isOneToOne: false
            referencedRelation: "indications"
            referencedColumns: ["id"]
          },
        ]
      }
      companies: {
        Row: {
          canonical_name: string
          cik: string | null
          country: string | null
          created_at: string | null
          id: number
          market_cap: number | null
          ticker: string | null
          updated_at: string | null
          website: string | null
        }
        Insert: {
          canonical_name: string
          cik?: string | null
          country?: string | null
          created_at?: string | null
          id?: number
          market_cap?: number | null
          ticker?: string | null
          updated_at?: string | null
          website?: string | null
        }
        Update: {
          canonical_name?: string
          cik?: string | null
          country?: string | null
          created_at?: string | null
          id?: number
          market_cap?: number | null
          ticker?: string | null
          updated_at?: string | null
          website?: string | null
        }
        Relationships: []
      }
      drug_indications: {
        Row: {
          drug_id: number
          indication_id: number
        }
        Insert: {
          drug_id: number
          indication_id: number
        }
        Update: {
          drug_id?: number
          indication_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "drug_indications_drug_id_fkey"
            columns: ["drug_id"]
            isOneToOne: false
            referencedRelation: "drugs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "drug_indications_indication_id_fkey"
            columns: ["indication_id"]
            isOneToOne: false
            referencedRelation: "indications"
            referencedColumns: ["id"]
          },
        ]
      }
      drug_targets: {
        Row: {
          drug_id: number
          target_id: number
        }
        Insert: {
          drug_id: number
          target_id: number
        }
        Update: {
          drug_id?: number
          target_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "drug_targets_drug_id_fkey"
            columns: ["drug_id"]
            isOneToOne: false
            referencedRelation: "drugs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "drug_targets_target_id_fkey"
            columns: ["target_id"]
            isOneToOne: false
            referencedRelation: "targets"
            referencedColumns: ["id"]
          },
        ]
      }
      drugs: {
        Row: {
          active_ingredient: string | null
          company_id: number | null
          created_at: string | null
          id: number
          mechanism: string | null
          preferred_name: string
        }
        Insert: {
          active_ingredient?: string | null
          company_id?: number | null
          created_at?: string | null
          id?: number
          mechanism?: string | null
          preferred_name: string
        }
        Update: {
          active_ingredient?: string | null
          company_id?: number | null
          created_at?: string | null
          id?: number
          mechanism?: string | null
          preferred_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "drugs_company_id_fkey"
            columns: ["company_id"]
            isOneToOne: false
            referencedRelation: "companies"
            referencedColumns: ["id"]
          },
        ]
      }
      epi_estimates: {
        Row: {
          created_at: string | null
          geography: string | null
          id: number
          indication_id: number | null
          metric: string | null
          source: string | null
          value: number | null
          year: number | null
        }
        Insert: {
          created_at?: string | null
          geography?: string | null
          id?: number
          indication_id?: number | null
          metric?: string | null
          source?: string | null
          value?: number | null
          year?: number | null
        }
        Update: {
          created_at?: string | null
          geography?: string | null
          id?: number
          indication_id?: number | null
          metric?: string | null
          source?: string | null
          value?: number | null
          year?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "epi_estimates_indication_id_fkey"
            columns: ["indication_id"]
            isOneToOne: false
            referencedRelation: "indications"
            referencedColumns: ["id"]
          },
        ]
      }
      filings: {
        Row: {
          cash_usd: number | null
          cik: string | null
          company_id: number | null
          created_at: string | null
          filing_date: string | null
          form_type: string | null
          id: number
          revenue_usd: number | null
          rnd_expense_usd: number | null
          url: string | null
        }
        Insert: {
          cash_usd?: number | null
          cik?: string | null
          company_id?: number | null
          created_at?: string | null
          filing_date?: string | null
          form_type?: string | null
          id?: number
          revenue_usd?: number | null
          rnd_expense_usd?: number | null
          url?: string | null
        }
        Update: {
          cash_usd?: number | null
          cik?: string | null
          company_id?: number | null
          created_at?: string | null
          filing_date?: string | null
          form_type?: string | null
          id?: number
          revenue_usd?: number | null
          rnd_expense_usd?: number | null
          url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "filings_company_id_fkey"
            columns: ["company_id"]
            isOneToOne: false
            referencedRelation: "companies"
            referencedColumns: ["id"]
          },
        ]
      }
      indications: {
        Row: {
          created_at: string | null
          description: string | null
          icd10: string | null
          id: number
          label: string
          mesh_id: string | null
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          icd10?: string | null
          id?: number
          label: string
          mesh_id?: string | null
        }
        Update: {
          created_at?: string | null
          description?: string | null
          icd10?: string | null
          id?: number
          label?: string
          mesh_id?: string | null
        }
        Relationships: []
      }
      synonyms: {
        Row: {
          canonical_id: number
          created_at: string | null
          entity_type: string | null
          id: number
          name: string
          source: string | null
        }
        Insert: {
          canonical_id: number
          created_at?: string | null
          entity_type?: string | null
          id?: number
          name: string
          source?: string | null
        }
        Update: {
          canonical_id?: number
          created_at?: string | null
          entity_type?: string | null
          id?: number
          name?: string
          source?: string | null
        }
        Relationships: []
      }
      targets: {
        Row: {
          created_at: string | null
          gene_symbol: string | null
          id: number
          name: string | null
          uniprot_id: string | null
        }
        Insert: {
          created_at?: string | null
          gene_symbol?: string | null
          id?: number
          name?: string | null
          uniprot_id?: string | null
        }
        Update: {
          created_at?: string | null
          gene_symbol?: string | null
          id?: number
          name?: string | null
          uniprot_id?: string | null
        }
        Relationships: []
      }
      trial_indications: {
        Row: {
          indication_id: number
          trial_id: string
        }
        Insert: {
          indication_id: number
          trial_id: string
        }
        Update: {
          indication_id?: number
          trial_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "trial_indications_indication_id_fkey"
            columns: ["indication_id"]
            isOneToOne: false
            referencedRelation: "indications"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trial_indications_trial_id_fkey"
            columns: ["trial_id"]
            isOneToOne: false
            referencedRelation: "trials"
            referencedColumns: ["id"]
          },
        ]
      }
      trials: {
        Row: {
          fetched_at: string | null
          id: string
          last_updated: string | null
          phase: string | null
          primary_completion_date: string | null
          source: string | null
          sponsor_company_id: number | null
          start_date: string | null
          status: string | null
          title: string | null
        }
        Insert: {
          fetched_at?: string | null
          id: string
          last_updated?: string | null
          phase?: string | null
          primary_completion_date?: string | null
          source?: string | null
          sponsor_company_id?: number | null
          start_date?: string | null
          status?: string | null
          title?: string | null
        }
        Update: {
          fetched_at?: string | null
          id?: string
          last_updated?: string | null
          phase?: string | null
          primary_completion_date?: string | null
          source?: string | null
          sponsor_company_id?: number | null
          start_date?: string | null
          status?: string | null
          title?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trials_sponsor_company_id_fkey"
            columns: ["sponsor_company_id"]
            isOneToOne: false
            referencedRelation: "companies"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      search_mv: {
        Row: {
          description: string | null
          entity_id: string | null
          entity_type: string | null
          search_vector: unknown | null
          title: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      refresh_search_mv: {
        Args: Record<PropertyKey, never>
        Returns: undefined
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
