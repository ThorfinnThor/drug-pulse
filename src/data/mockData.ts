// Mock data for the pharma intelligence platform

export interface Company {
  id: number;
  name: string;
  ticker?: string;
  country: string;
  marketCap?: number;
  pipelineAssets: number;
  upcomingReadouts: number;
  latestFiling?: string;
  description: string;
}

export interface Drug {
  id: number;
  name: string;
  company: string;
  companyId: number;
  mechanism: string;
  indications: string[];
  phase: string;
  status: string;
  nextMilestone?: string;
  competitors: Array<{
    name: string;
    company: string;
    phase: string;
  }>;
}

export interface Trial {
  id: string;
  title: string;
  phase: string;
  status: string;
  sponsor: string;
  indication: string;
  startDate: string;
  completionDate: string;
  enrollment: number;
  sites: number;
}

export interface Indication {
  id: number;
  name: string;
  description: string;
  prevalence: string;
  marketSize: string;
  trialsCount: {
    phase1: number;
    phase2: number;
    phase3: number;
    phase4: number;
  };
  lateStageTrials: Trial[];
}

export const mockCompanies: Company[] = [
  {
    id: 1,
    name: "Pfizer Inc.",
    ticker: "PFE",
    country: "United States",
    marketCap: 275000000000,
    pipelineAssets: 95,
    upcomingReadouts: 12,
    latestFiling: "2024-02-15",
    description: "Global pharmaceutical company focusing on innovative medicines and vaccines."
  },
  {
    id: 2,
    name: "Roche Holding AG",
    ticker: "ROG",
    country: "Switzerland", 
    marketCap: 245000000000,
    pipelineAssets: 78,
    upcomingReadouts: 8,
    latestFiling: "2024-02-12",
    description: "Leading biotech company with focus on oncology and personalized healthcare."
  },
  {
    id: 3,
    name: "Moderna Inc.",
    ticker: "MRNA",
    country: "United States",
    marketCap: 42000000000,
    pipelineAssets: 45,
    upcomingReadouts: 15,
    latestFiling: "2024-02-20",
    description: "mRNA technology company developing vaccines and therapeutics."
  },
  {
    id: 4,
    name: "BioNTech SE",
    ticker: "BNTX",
    country: "Germany",
    marketCap: 25000000000,
    pipelineAssets: 25,
    upcomingReadouts: 6,
    latestFiling: "2024-02-10",
    description: "Immunotherapy company developing cancer vaccines and mRNA therapeutics."
  },
  {
    id: 5,
    name: "Gilead Sciences",
    ticker: "GILD",
    country: "United States",
    marketCap: 78000000000,
    pipelineAssets: 52,
    upcomingReadouts: 9,
    latestFiling: "2024-02-18",
    description: "Biopharmaceutical company focused on antiviral drugs and oncology."
  }
];

export const mockDrugs: Drug[] = [
  {
    id: 1,
    name: "Darolutamide",
    company: "Bayer AG",
    companyId: 6,
    mechanism: "Androgen Receptor Antagonist",
    indications: ["Metastatic CRPC", "Non-metastatic CRPC"],
    phase: "Approved",
    status: "Commercial",
    competitors: [
      { name: "Enzalutamide", company: "Pfizer", phase: "Approved" },
      { name: "Apalutamide", company: "Janssen", phase: "Approved" },
      { name: "ARV-110", company: "Arvinas", phase: "Phase 2" }
    ]
  },
  {
    id: 2,
    name: "Trastuzumab Deruxtecan",
    company: "Daiichi Sankyo",
    companyId: 7,
    mechanism: "HER2-targeting ADC",
    indications: ["HER2+ Breast Cancer", "HER2+ Gastric Cancer"],
    phase: "Approved",
    status: "Commercial",
    nextMilestone: "DESTINY-Breast04 readout Q2 2024",
    competitors: [
      { name: "Trastuzumab", company: "Roche", phase: "Approved" },
      { name: "Pertuzumab", company: "Roche", phase: "Approved" },
      { name: "Margetuximab", company: "MacroGenics", phase: "Approved" }
    ]
  },
  {
    id: 3,
    name: "Sotorasib",
    company: "Amgen Inc.",
    companyId: 8,
    mechanism: "KRAS G12C Inhibitor",
    indications: ["NSCLC", "Colorectal Cancer"],
    phase: "Approved",
    status: "Commercial",
    nextMilestone: "CodeBreaK 300 readout Q3 2024",
    competitors: [
      { name: "Adagrasib", company: "Mirati", phase: "Approved" },
      { name: "GDC-6036", company: "Genentech", phase: "Phase 2" },
      { name: "JDQ443", company: "Novartis", phase: "Phase 2" }
    ]
  }
];

export const mockTrials: Trial[] = [
  {
    id: "NCT05123456",
    title: "Phase 3 Study of Darolutamide in Metastatic CRPC",
    phase: "3",
    status: "Active, not recruiting",
    sponsor: "Bayer AG",
    indication: "Metastatic Castration-Resistant Prostate Cancer",
    startDate: "2022-03-15",
    completionDate: "2025-06-30",
    enrollment: 1200,
    sites: 85
  },
  {
    id: "NCT05234567",
    title: "T-DXd vs Standard of Care in HER2-Low Breast Cancer",
    phase: "3",
    status: "Recruiting",
    sponsor: "Daiichi Sankyo",
    indication: "HER2-Low Breast Cancer",
    startDate: "2023-01-10",
    completionDate: "2026-12-15",
    enrollment: 557,
    sites: 120
  },
  {
    id: "NCT05345678",
    title: "Sotorasib + Pembrolizumab in KRAS G12C NSCLC",
    phase: "2",
    status: "Active, not recruiting",
    sponsor: "Amgen Inc.",
    indication: "Non-Small Cell Lung Cancer",
    startDate: "2022-08-20",
    completionDate: "2024-11-30",
    enrollment: 325,
    sites: 45
  },
  {
    id: "NCT05456789",
    title: "mRNA-1273 Seasonal Influenza Vaccine Study",
    phase: "2",
    status: "Recruiting", 
    sponsor: "Moderna Inc.",
    indication: "Influenza Prevention",
    startDate: "2023-09-01",
    completionDate: "2025-03-31",
    enrollment: 2400,
    sites: 65
  }
];

export const mockIndications: Indication[] = [
  {
    id: 1,
    name: "Metastatic Castration-Resistant Prostate Cancer",
    description: "Advanced prostate cancer that has spread and no longer responds to hormone therapy",
    prevalence: "~280,000 patients globally",
    marketSize: "$8.2B (2023)",
    trialsCount: {
      phase1: 25,
      phase2: 45,
      phase3: 12,
      phase4: 8
    },
    lateStageTrials: [
      {
        id: "NCT05123456",
        title: "Phase 3 Study of Darolutamide in Metastatic CRPC",
        phase: "3",
        status: "Active, not recruiting",
        sponsor: "Bayer AG",
        indication: "Metastatic Castration-Resistant Prostate Cancer",
        startDate: "2022-03-15",
        completionDate: "2025-06-30",
        enrollment: 1200,
        sites: 85
      },
      {
        id: "NCT05789012",
        title: "VISION-2: Lutetium-177-PSMA-617 in mCRPC",
        phase: "3",
        status: "Recruiting",
        sponsor: "Novartis",
        indication: "Metastatic Castration-Resistant Prostate Cancer",
        startDate: "2023-05-12",
        completionDate: "2026-08-15",
        enrollment: 850,
        sites: 95
      }
    ]
  },
  {
    id: 2,
    name: "HER2-Positive Breast Cancer",
    description: "Breast cancer characterized by overexpression of HER2 protein",
    prevalence: "~320,000 patients globally",
    marketSize: "$12.5B (2023)",
    trialsCount: {
      phase1: 42,
      phase2: 68,
      phase3: 18,
      phase4: 12
    },
    lateStageTrials: [
      {
        id: "NCT05234567",
        title: "T-DXd vs Standard of Care in HER2-Low Breast Cancer",
        phase: "3",
        status: "Recruiting",
        sponsor: "Daiichi Sankyo",
        indication: "HER2-Low Breast Cancer",
        startDate: "2023-01-10",
        completionDate: "2026-12-15",
        enrollment: 557,
        sites: 120
      }
    ]
  },
  {
    id: 3,
    name: "Non-Small Cell Lung Cancer",
    description: "The most common type of lung cancer, accounting for ~85% of cases",
    prevalence: "~1.8M patients globally",
    marketSize: "$18.9B (2023)",
    trialsCount: {
      phase1: 125,
      phase2: 245,
      phase3: 65,
      phase4: 32
    },
    lateStageTrials: [
      {
        id: "NCT05345678",
        title: "Sotorasib + Pembrolizumab in KRAS G12C NSCLC",
        phase: "2",
        status: "Active, not recruiting",
        sponsor: "Amgen Inc.",
        indication: "Non-Small Cell Lung Cancer",
        startDate: "2022-08-20",
        completionDate: "2024-11-30",
        enrollment: 325,
        sites: 45
      }
    ]
  }
];

export const searchAllEntities = (query: string) => {
  const results: Array<{
    type: 'company' | 'drug' | 'trial' | 'indication';
    id: string | number;
    name: string;
    subtitle?: string;
  }> = [];

  // Search companies
  mockCompanies.forEach(company => {
    if (company.name.toLowerCase().includes(query.toLowerCase()) ||
        company.ticker?.toLowerCase().includes(query.toLowerCase())) {
      results.push({
        type: 'company',
        id: company.id,
        name: company.name,
        subtitle: company.ticker ? `${company.ticker} • ${company.country}` : company.country
      });
    }
  });

  // Search drugs
  mockDrugs.forEach(drug => {
    if (drug.name.toLowerCase().includes(query.toLowerCase()) ||
        drug.mechanism.toLowerCase().includes(query.toLowerCase())) {
      results.push({
        type: 'drug',
        id: drug.id,
        name: drug.name,
        subtitle: `${drug.company} • ${drug.mechanism}`
      });
    }
  });

  // Search trials
  mockTrials.forEach(trial => {
    if (trial.title.toLowerCase().includes(query.toLowerCase()) ||
        trial.id.toLowerCase().includes(query.toLowerCase()) ||
        trial.indication.toLowerCase().includes(query.toLowerCase())) {
      results.push({
        type: 'trial',
        id: trial.id,
        name: trial.title,
        subtitle: `${trial.id} • Phase ${trial.phase}`
      });
    }
  });

  // Search indications
  mockIndications.forEach(indication => {
    if (indication.name.toLowerCase().includes(query.toLowerCase())) {
      results.push({
        type: 'indication',
        id: indication.id,
        name: indication.name,
        subtitle: indication.prevalence
      });
    }
  });

  return results.slice(0, 10); // Limit results
};