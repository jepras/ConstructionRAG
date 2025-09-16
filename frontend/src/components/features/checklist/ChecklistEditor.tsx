'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

interface ChecklistEditorProps {
  checklist: string;
  onChecklistChange: (value: string) => void;
}

const SAVED_CHECKLISTS = [
  { 
    id: 'construction-infrastructure', 
    name: 'IT Infrastructure & Network',
    content: `1. Netværksporte
1.1 Antal: [FUNDET/MANGLER] Findes der en plantegning med markering af netværksudtag?
1.2 Type: [FUNDET/MANGLER] Er der krav til port-hastighed (1 Gbit/s, 10 Gbit/s)? Skal der være PoE (Power over Ethernet)?

2. Serverinstallation
2.1 IP Adresser: [FUNDET/MANGLER/FORUDSÆTNING] Leverer kunden faste IP-adresser til servere og netværksudstyr?
2.2 Firewall: [FUNDET/MANGLER] Er der specificeret regler for firewall-åbninger for systemkommunikation?

3. Wi-Fi
3.1 Dækning: [FUNDET/MANGLER] Er der krav til Wi-Fi dækning i specifikke områder?`
  },
  { 
    id: 'construction-aia', 
    name: 'AIA (Indbruds-alarm)',
    content: `1. Generel AIA Information
1.1 Sikringsniveau: [FUNDET/MANGLER/RISIKO] Er der specificeret et F&P sikringsniveau (f.eks. 20S, 30, 40)?
1.2 Systemvalg: [FUNDET/MANGLER] Er der krav til specifikke fabrikater (f.eks. Ajax, Scantron)?

2. Komponenter
2.1 Centraler: [FUNDET/MANGLER] Antal alarmcentraler og udvidelsesmoduler?
2.2 Detektorer: [FUNDET/MANGLER] Type og antal (PIR, kombi, gardin, glasbrud)?
2.3 Sirener: [FUNDET/MANGLER] Indendørs og udendørs sirener?

3. Installation
3.1 Højde: [FORUDSÆTNING] Montagehøjde maksimalt 4 meter fra stige?
3.2 Kabling: [FUNDET/MANGLER] Skal der etableres nye føringsveje?`
  },
  { 
    id: 'construction-full', 
    name: 'Komplet Bygningssikkerhed (Standard)',
    content: `1. Generel Projekt- og Dokumentinformation
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
7.4 Salgs- og Leveringsbetingelser: [FORUDSÆTNING] Notér, at tilbuddet er baseret på egne standard salgs- og leveringsbetingelser.`
  }
];

export default function ChecklistEditor({ checklist, onChecklistChange }: ChecklistEditorProps) {
  const [selectedChecklistId, setSelectedChecklistId] = React.useState<string>('');

  const handleChecklistSelect = (checklistId: string) => {
    const selectedChecklist = SAVED_CHECKLISTS.find(c => c.id === checklistId);
    if (selectedChecklist) {
      onChecklistChange(selectedChecklist.content);
      setSelectedChecklistId(checklistId);
      toast.success(`Loaded checklist: ${selectedChecklist.name}`);
    }
  };

  const handleSaveChanges = () => {
    toast.success("Changes saved successfully!");
  };

  const handleSaveAsNew = () => {
    toast.success("Saved as new checklist!");
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Select a pre-saved checklist
        </label>
        <Select value={selectedChecklistId} onValueChange={handleChecklistSelect}>
          <SelectTrigger className="bg-input">
            <SelectValue placeholder="Choose a checklist template" />
          </SelectTrigger>
          <SelectContent>
            {SAVED_CHECKLISTS.map((checklist) => (
              <SelectItem key={checklist.id} value={checklist.id}>
                {checklist.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Checklist Items
        </label>
        <textarea
          value={checklist}
          onChange={(e) => onChecklistChange(e.target.value)}
          className="w-full h-64 p-3 border border-border rounded-md bg-input text-foreground font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="Enter your checklist items..."
        />
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={handleSaveChanges}>
          Save Changes
        </Button>
        <Button variant="outline" onClick={handleSaveAsNew}>
          Save as New
        </Button>
      </div>
    </div>
  );
}