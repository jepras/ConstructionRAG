'use client';

import React from 'react';
import { Play, Save, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { FileDropzone } from '@/components/upload/FileDropzone';
import ChecklistBox from '@/components/features/checklist/ChecklistBox';
import ChecklistEditor from '@/components/features/checklist/ChecklistEditor';
import AnalysisResults from '@/components/features/checklist/AnalysisResults';
import ResultsTable, { ChecklistResult } from '@/components/features/checklist/ResultsTable';

interface ProjectChecklistContentProps {
  projectSlug: string;
  runId: string;
  isAuthenticated: boolean;
  user: any;
}

// Mock data for existing analysis runs
const MOCK_ANALYSIS_RUNS = [
  {
    id: 'analysis-001',
    name: 'Initial Security Assessment - 2024-01-15',
    date: '2024-01-15T10:30:00Z',
    checklist: 'Komplet Bygningssikkerhed (Standard)',
    status: 'completed'
  },
  {
    id: 'analysis-002', 
    name: 'AIA System Review - 2024-01-20',
    date: '2024-01-20T14:15:00Z',
    checklist: 'AIA (Indbruds-alarm)',
    status: 'completed'
  },
  {
    id: 'analysis-003',
    name: 'IT Infrastructure Check - 2024-01-22',
    date: '2024-01-22T09:45:00Z',
    checklist: 'IT Infrastructure & Network',
    status: 'completed'
  }
];

// Mock analysis results
const MOCK_ANALYSIS_RESULTS: ChecklistResult[] = [
  {
    id: '1',
    number: '1.1',
    name: 'Projektidentifikation',
    status: 'found',
    description: 'Projektnavn, adresse og bygherre er tydeligt angivet i dokumentation.',
    source: {
      document: 'Projektbeskrivelse.pdf',
      page: 2
    }
  },
  {
    id: '2',
    number: '1.3',
    name: 'Sikringsniveau/Klasse',
    status: 'pending_clarification',
    description: 'F&P sikringsniveau er nævnt men ikke specifikt defineret. Behov for afklaring af korrekt klasse.',
    source: {
      document: 'Sikkerhedsspecifikation.pdf',
      page: 7
    }
  },
  {
    id: '3',
    number: '2.1',
    name: 'AIA Omfang og Placering',
    status: 'missing',
    description: 'Plantegninger med detaljeret placering af detektorer og sirener mangler.',
  },
  {
    id: '4',
    number: '3.3',
    name: 'Elektrisk Aflåsning',
    status: 'risk',
    description: 'Ansvar for låse-installation er ikke afklaret mellem leverandører. Høj risiko for forsinkelser.',
    source: {
      document: 'Dørskema.pdf',
      page: 12
    }
  },
  {
    id: '5',
    number: '6.2',
    name: 'Strøm (230V)',
    status: 'conditions',
    description: 'Strømforsyning forudsættes etableret af autoriseret elektriker før installation.',
    source: {
      document: 'Elinstallationsplan.pdf',
      page: 4
    }
  },
  {
    id: '6',
    number: '7.2',
    name: 'Serviceaftale',
    status: 'found',
    description: 'Årlig serviceaftale med batteriskift og eftersyn er specificeret.',
    source: {
      document: 'Servicekontrakt.pdf',
      page: 1
    }
  }
];

const MOCK_RAW_OUTPUT = `CHECKLIST ANALYSIS RESULTS - Downtown Tower Project

=== ANALYSIS SUMMARY ===
Total items analyzed: 25
Found: 8 items
Missing: 6 items  
Risk: 3 items
Conditions: 5 items
Pending Clarification: 3 items

=== DETAILED FINDINGS ===

[FOUND] 1.1 Projektidentifikation
- Status: FOUND
- Source: Projektbeskrivelse.pdf, side 2
- Details: Projektnavn "Downtown Tower", adresse "Hovedgade 123, 2100 København Ø", bygherre "Copenhagen Properties A/S" er tydeligt angivet.

[PENDING_CLARIFICATION] 1.3 Sikringsniveau/Klasse  
- Status: PENDING_CLARIFICATION
- Source: Sikkerhedsspecifikation.pdf, side 7
- Details: Dokumentet nævner "høj sikkerhed" men specificerer ikke EN-klasse eller F&P niveau. Forsikringsgodkendelse kræver præcis klassificering.

[MISSING] 2.1 AIA Omfang og Placering
- Status: MISSING
- Source: N/A
- Details: Plantegninger med detaljeret placering af centrale, detektorer og sirener er ikke tilgængelige. Dette er kritisk for korrekt prisestimering.

[RISK] 3.3 Elektrisk Aflåsning
- Status: RISK  
- Source: Dørskema.pdf, side 12
- Details: Ansvar for låse-installation er uklart mellem sikkerhedsleverandør og tømrer. Høj risiko for konflikter og forsinkelser.

[CONDITIONS] 6.2 Strøm (230V)
- Status: CONDITIONS
- Source: Elinstallationsplan.pdf, side 4  
- Details: 230V forsyning forudsættes etableret af kundens autoriserede elektriker før sikkerhedsinstallation kan påbegyndes.

[FOUND] 7.2 Serviceaftale
- Status: FOUND
- Source: Servicekontrakt.pdf, side 1
- Details: Årlig serviceaftale inkluderer batteriskift, funktionstest og softwareopdateringer. Abonnementspris: DKK 12.000/år.

=== RECOMMENDATIONS ===
1. Afklar sikringsniveau med forsikringsselskab
2. Indhent detaljerede plantegninger for AIA-installation  
3. Definer ansvar for dørlåse i kontrakt
4. Bekræft strømforsyning er klar før opstart
5. Gennemgå alle dokumenter for manglende tekniske specifikationer`;

const DEFAULT_CHECKLIST = `1. Generel Projekt- og Dokumentinformation
1.1 Projektidentifikation: [FUNDET/MANGLER] Projektnavn, adresse og bygherre.
1.2 Dokumentgrundlag: [FUNDET/MANGLER] Liste over alle modtagne dokumenter (beskrivelser, tegninger, dørskemaer, tilbudslister etc.).
1.3 Sikringsniveau/Klasse: [FUNDET/MANGLER/RISIKO] Er der specificeret et F&P sikringsniveau (f.eks. 20S, 30, 40) eller en EN-klasse (Grade 2, 3) for AIA? Risiko: Hvis det mangler, skal der tages forbehold for, at installationen ikke nødvendigvis godkendes af forsikringen.
1.4 Systemvalg: [FUNDET/MANGLER] Er der krav til specifikke fabrikater (f.eks. Salto, Ajax, Scantron, NOX, SPC) eller er der frit valg?

2. AIA (Indbruds-alarm)
2.1 Omfang og Placering: [FUNDET/MANGLER] Findes plantegninger, der viser placering og antal af central, betjeningspaneler, detektorer og sirener? Dette er altafgørende for prisen.
2.2 Komponentliste: [FUNDET/MANGLER] Optæl antal af: Alarmcentraler og udvidelsesmoduler. Betjeningspaneler (type: touch, knapper). Detektorer (type: PIR, kombi, gardin, glasbrud, åbning). Sirener (indendørs/udendørs). Overfaldstryk.
2.3 Alarmoverførsel: [FUNDET/MANGLER] Hvem er kontrolcentral? Hvordan transmitteres der (IP/GSM)? Er SIM-kort og abonnement inkluderet?
2.4 Forudsætninger: [FORUDSÆTNING] Notér forbehold som f.eks.: Antal detektorer er tilstrækkeligt for rumindretning. Korrekt højde til loft (typisk max 4 meter). Gardindetektorers frie "synsfelt".

3. ADK (Adgangskontrol)
3.1 Omfang og Placering: [FUNDET/MANGLER] Findes dørskema og plantegninger, der viser, hvilke døre der skal have ADK, samt type (online/offline)?
3.2 Komponentliste: [FUNDET/MANGLER] Optæl antal af: Online døre (fortrådede med kontrolboks/dørcontroller). Offline/trådløse døre (batteridrevne langskilte/cylindere). Gateways/opdateringspunkter. Programmeringsenhed (PPD/bordkoder). Adgangsmedier (brikker/kort - antal og type: Mifare, DESFire).
3.3 Elektrisk Aflåsning (KRITISK GRÆNSEFLADE): [FUNDET/MANGLER/RISIKO] Hvilken type lås (motorlås, el-slutblik)? Hvem leverer og monterer låsen og forbereder døren/karmen? Risiko: Uklarhed her kan medføre store ekstraomkostninger og forsinkelser.
3.4 Software & IT: [FUNDET/MANGLER] Skal software installeres på kundens PC/server eller leveres der en dedikeret server? Hvem leverer netværksporte og konfigurerer IP-adresser?
3.5 Mekanisk Dørkontrol (MEK): [FUNDET/MANGLER] Skal serviceaftalen indeholde mekanisk eftersyn af døre (smøring af hængsler, justering af dørpumper etc.)?

4. TVO (Videoovervågning)
4.1 Omfang og Placering: [FUNDET/MANGLER] Findes plantegninger med kameraplaceringer?
4.2 Komponentliste: [FUNDET/MANGLER] Optæl antal af: Kameraer (type: turret, bullet, dome; opløsning: MP; linse: mm). Optager/NVR (antal kanaler, harddiskstørelse i TB). POE-switches.
4.3 Forudsætninger: [FORUDSÆTNING] Notér forbehold som f.eks. montagehøjde (f.eks. max 3,5 meter fra stige) og om liftleje er ekskluderet.

5. Dørtelefoni
5.1 Omfang og Placering: [FUNDET/MANGLER] Findes der tegninger/beskrivelse af antal opgange, dørstationer og lejligheder?
5.2 Komponentliste: [FUNDET/MANGLER] Optæl antal af: Dørtableauer (type: planforsænket/påbygget; antal ringetryk). Svartelefoner (type: audio/video). Centraludstyr (strømforsyning, video-convertere). El-slutblik (antal, og hvem der monterer).
5.3 Kabling: [FUNDET/MANGLER/RISIKO] Skal eksisterende kabling genanvendes, eller skal der trækkes ny? Risiko: Genbrug af gammel kabling er en stor risiko for fejl og merarbejde.

6. Installation, Forudsætninger og Grænseflader
6.1 Føringsveje: [FUNDET/MANGLER/FORUDSÆTNING] Er der forberedte føringsveje med træksnor, eller skal der etableres nye (f.eks. synlig i hvid kabelkanal)?
6.2 Strøm (230V): [FUNDET/MANGLER/FORUDSÆTNING] Er der 230V til rådighed ved centraludstyr? Er dette inkluderet, eller skal det leveres af en autoriseret elektriker?
6.3 Brandlukninger: [FUNDET/MANGLER/FORUDSÆTNING] Er brandlukninger inkluderet, eller udføres de af anden entreprise? Typisk en forudsætning, at det er ekskluderet.
6.4 Projektledelse og Dokumentation: [FUNDET/MANGLER] Er der specificeret antal byggemøder, krav til D&V, KS, og installationserklæringer?

7. Økonomi og Aftalevilkår
7.1 Økonomisk Model: [FUNDET/MANGLER] Er der ønske om kontantkøb, abonnementsaftale eller begge dele som option?
7.2 Serviceaftale: [FUNDET/MANGLER] Er en serviceaftale et krav? Hvad skal den indeholde (f.eks. årligt eftersyn, batteriskift, softwareopdatering)?
7.3 Optioner: [FUNDET/MANGLER] Er der beskrevet optioner eller tillægsydelser, der skal prissættes separat?
7.4 Salgs- og Leveringsbetingelser: [FORUDSÆTNING] Notér, at tilbuddet er baseret på egne standard salgs- og leveringsbetingelser.`;

export default function ProjectChecklistContent({ 
  projectSlug, 
  runId, 
  isAuthenticated, 
  user 
}: ProjectChecklistContentProps) {
  const [selectedAnalysisRun, setSelectedAnalysisRun] = React.useState<string>('');
  const [uploadedFiles, setUploadedFiles] = React.useState<File[]>([]);
  const [checklist, setChecklist] = React.useState<string>(DEFAULT_CHECKLIST);
  const [isAnalyzing, setIsAnalyzing] = React.useState<boolean>(false);
  const [hasAnalyzed, setHasAnalyzed] = React.useState<boolean>(false);
  const [analysisResults, setAnalysisResults] = React.useState<ChecklistResult[]>([]);
  const [rawOutput, setRawOutput] = React.useState<string>('');

  const handleFilesSelected = (files: File[]) => {
    setUploadedFiles(files);
    toast.success(`${files.length} PDF files uploaded successfully`);
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(files => files.filter((_, i) => i !== index));
  };

  const handleAnalysisRunSelect = (runId: string) => {
    const selectedRun = MOCK_ANALYSIS_RUNS.find(run => run.id === runId);
    if (selectedRun) {
      setSelectedAnalysisRun(runId);
      setHasAnalyzed(true);
      setAnalysisResults(MOCK_ANALYSIS_RESULTS);
      setRawOutput(MOCK_RAW_OUTPUT);
      toast.success(`Loaded analysis: ${selectedRun.name}`);
    }
  };

  const handleAnalyze = async () => {
    if (uploadedFiles.length === 0) {
      toast.error("Please upload at least one PDF file");
      return;
    }
    
    if (!checklist.trim()) {
      toast.error("Please define a checklist");
      return;
    }

    setIsAnalyzing(true);
    
    // Simulate analysis process
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    setHasAnalyzed(true);
    setAnalysisResults(MOCK_ANALYSIS_RESULTS);
    setRawOutput(MOCK_RAW_OUTPUT);
    setIsAnalyzing(false);
    
    toast.success("Analysis completed successfully!");
  };

  const handleSaveAnalysis = () => {
    toast.success("Analysis run saved successfully!");
  };

  const handleExportPDF = () => {
    toast.success("Exporting analysis to PDF...");
  };

  const handleExportCSV = () => {
    toast.success("Exporting analysis to CSV...");
  };

  return (
    <div className="p-6 space-y-6">
      {/* Box 0: Existing Analysis Runs */}
      <ChecklistBox 
        title="Load Existing Analysis" 
        number={0}
        defaultOpen={false}
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Select a previous analysis run to load the checklist and results.
          </p>
          <Select value={selectedAnalysisRun} onValueChange={handleAnalysisRunSelect}>
            <SelectTrigger className="bg-input">
              <SelectValue placeholder="Choose an existing analysis run" />
            </SelectTrigger>
            <SelectContent>
              {MOCK_ANALYSIS_RUNS.map((run) => (
                <SelectItem key={run.id} value={run.id}>
                  <div className="flex flex-col">
                    <span className="font-medium">{run.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(run.date).toLocaleDateString()} • {run.checklist}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </ChecklistBox>

      {/* Box 1: Upload PDF Files */}
      <ChecklistBox 
        title="Upload Your PDF Files" 
        number={1}
        defaultOpen={true}
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Select construction documents, specifications, and drawings
          </p>
          <FileDropzone
            onFilesSelected={handleFilesSelected}
            selectedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
            maxFiles={10}
            showValidation={false}
          />
        </div>
      </ChecklistBox>

      {/* Box 2: Define Checklist */}
      <ChecklistBox 
        title="Define Checklist" 
        number={2}
        defaultOpen={true}
      >
        <ChecklistEditor 
          checklist={checklist}
          onChecklistChange={setChecklist}
        />
      </ChecklistBox>

      {/* Analyze Button */}
      <div className="flex justify-center py-4">
        <Button 
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          size="lg"
          className="px-8"
        >
          {isAnalyzing ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground mr-2"></div>
              Analyzing...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Analyze Checklist
            </>
          )}
        </Button>
      </div>

      {hasAnalyzed && (
        <>
          {/* Box 3: Raw LLM Output */}
          <ChecklistBox 
            title="Raw LLM Output" 
            number={3}
            defaultOpen={false}
          >
            <AnalysisResults rawOutput={rawOutput} />
          </ChecklistBox>

          {/* Box 4: Structured Results */}
          <ChecklistBox 
            title="Structured Results" 
            number={4}
            defaultOpen={true}
          >
            <ResultsTable results={analysisResults} />
          </ChecklistBox>

          {/* Box 5: Save/Export */}
          <ChecklistBox 
            title="Save/Export" 
            number={5}
            defaultOpen={false}
          >
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Save Analysis</p>
                <Button onClick={handleSaveAnalysis} variant="outline" className="w-full">
                  <Save className="mr-2 h-4 w-4" />
                  Save Analysis Run
                </Button>
              </div>
              
              <Separator />
              
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Export Results</p>
                <div className="grid grid-cols-2 gap-2">
                  <Button onClick={handleExportPDF} variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    Export PDF
                  </Button>
                  <Button onClick={handleExportCSV} variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    Export CSV
                  </Button>
                </div>
              </div>
            </div>
          </ChecklistBox>
        </>
      )}
    </div>
  );
}