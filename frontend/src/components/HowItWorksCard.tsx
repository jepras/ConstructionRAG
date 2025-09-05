import { ReactNode } from "react";
import { ArrowRight, Plus } from "lucide-react";

interface HowItWorksCardProps {
  step: number;
  title: string;
  description: string;
  children: ReactNode;
}

export default function HowItWorksCard({ step, title, description, children }: HowItWorksCardProps) {
  return (
    <div className="text-center">
      <div className="bg-card border border-border rounded-lg p-8 mb-6">
        <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold text-primary-foreground">
          {step}
        </div>
        <h3 className="text-xl font-semibold mb-4 text-card-foreground">{title}</h3>
        <div className="mb-6">
          {children}
        </div>
        <p className="text-muted-foreground text-sm">
          {description}
        </p>
      </div>
    </div>
  );
}

export function ProcessingDiagram() {
  return (
    <div className="flex items-stretch justify-center w-full h-full gap-1 text-foreground">
      {/* Inputs */}
      <div className="p-3 bg-card rounded-lg border border-border flex flex-col items-center justify-center text-center gap-3">
        <div className="flex flex-col items-center gap-2">
          <div className="w-6 h-6 bg-red-400 rounded"></div>
          <div className="w-6 h-6 bg-green-400 rounded"></div>
        </div>
        <p className="text-xs font-medium leading-tight">Your project<br/>files</p>
      </div>

      {/* Arrow */}
      <div className="flex items-center">
        <ArrowRight className="w-5 h-5 flex-shrink-0" />
      </div>

      {/* Middle Processing Stack */}
      <div className="flex items-center">
        <div className="flex flex-col items-center justify-center gap-1.5">
            <div className="flex items-center gap-2 p-2 bg-card rounded-lg border border-border w-full">
                <div className="w-5 h-5 bg-yellow-400 rounded flex-shrink-0"></div>
                <span className="text-xs font-medium">Best practices</span>
            </div>
            <Plus className="w-3 h-3 text-muted-foreground" />
            <div className="flex items-center gap-2 p-2 bg-card rounded-lg border-2 border-primary w-full">
                <div className="w-5 h-5 bg-primary rounded flex-shrink-0"></div>
                <span className="text-xs font-bold text-foreground">AI crunch</span>
            </div>
            <Plus className="w-3 h-3 text-muted-foreground" />
            <div className="flex items-center gap-2 p-2 bg-card rounded-lg border border-border w-full">
                <div className="w-5 h-5 bg-green-400 rounded flex-shrink-0"></div>
                <span className="text-xs font-medium">Your checklist</span>
            </div>
        </div>
      </div>
      
      {/* Arrow */}
      <div className="flex items-center">
        <ArrowRight className="w-5 h-5 flex-shrink-0" />
      </div>
      
      {/* Output */}
      <div className="p-3 bg-card rounded-lg border border-border flex flex-col items-center justify-center text-center gap-3">
        <div className="w-8 h-8 bg-primary rounded"></div>
         <p className="text-xs font-medium leading-tight">Custom<br/>Overview</p>
      </div>
    </div>
  );
}