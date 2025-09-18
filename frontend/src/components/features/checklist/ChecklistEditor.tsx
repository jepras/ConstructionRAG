'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { apiClient, ChecklistTemplate, ChecklistTemplateRequest } from '@/lib/api-client';

interface ChecklistEditorProps {
  checklist: string;
  onChecklistChange: (value: string) => void;
}

interface SaveTemplateDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (name: string, isPublic: boolean, category: string) => void;
  defaultName?: string;
  isUpdate?: boolean;
}

function SaveTemplateDialog({ isOpen, onOpenChange, onSave, defaultName = '', isUpdate = false }: SaveTemplateDialogProps) {
  const [name, setName] = React.useState(defaultName);
  const [isPublic, setIsPublic] = React.useState(true);

  React.useEffect(() => {
    setName(defaultName);
  }, [defaultName]);

  const handleSave = () => {
    if (!name.trim()) {
      toast.error('Please enter a template name');
      return;
    }
    onSave(name.trim(), isPublic, 'custom');
    onOpenChange(false);
    setName('');
    setIsPublic(true);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isUpdate ? 'Update Template' : 'Save Template'}</DialogTitle>
          <DialogDescription>
            {isUpdate ? 'Update your checklist template.' : 'Save your checklist as a template for future use.'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="template-name">Template Name</Label>
            <Input
              id="template-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter template name..."
            />
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="is-public"
              checked={isPublic}
              onCheckedChange={(checked) => setIsPublic(!!checked)}
            />
            <Label htmlFor="is-public">Make template public (visible to all users)</Label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              {isUpdate ? 'Update' : 'Save'} Template
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function ChecklistEditor({ checklist, onChecklistChange }: ChecklistEditorProps) {
  const [templates, setTemplates] = React.useState<ChecklistTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = React.useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = React.useState<ChecklistTemplate | null>(null);
  const [saveDialogOpen, setSaveDialogOpen] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [loadingTemplates, setLoadingTemplates] = React.useState(true);

  // Track owned templates for anonymous users using localStorage
  const [ownedTemplates, setOwnedTemplates] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    // Load owned templates from localStorage for anonymous users
    const saved = localStorage.getItem('owned-checklist-templates');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setOwnedTemplates(new Set(parsed));
      } catch {
        // Ignore parsing errors
      }
    }
  }, []);

  const updateOwnedTemplates = (templateId: string) => {
    const newOwnedTemplates = new Set(ownedTemplates);
    newOwnedTemplates.add(templateId);
    setOwnedTemplates(newOwnedTemplates);
    localStorage.setItem('owned-checklist-templates', JSON.stringify([...newOwnedTemplates]));
  };

  React.useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const templatesData = await apiClient.getChecklistTemplates();
      setTemplates(templatesData);
    } catch (error) {
      console.error('Error loading templates:', error);
      toast.error('Failed to load templates');
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      onChecklistChange(template.content);
      setSelectedTemplateId(templateId);
      setSelectedTemplate(template);
      toast.success(`Loaded template: ${template.name}`);
    }
  };

  const handleSaveChanges = async () => {
    if (!selectedTemplate) {
      toast.error('No template selected to update');
      return;
    }

    // Check if user can update this template
    const canUpdate = selectedTemplate.is_owner || ownedTemplates.has(selectedTemplate.id);
    if (!canUpdate) {
      toast.error('You can only update templates you created');
      return;
    }

    try {
      setIsLoading(true);
      const request: ChecklistTemplateRequest = {
        name: selectedTemplate.name,
        content: checklist,
        category: selectedTemplate.category,
        is_public: selectedTemplate.is_public,
      };

      await apiClient.updateChecklistTemplate(selectedTemplate.id, request);
      toast.success('Template updated successfully!');
      await loadTemplates(); // Refresh templates
    } catch (error) {
      console.error('Error updating template:', error);
      toast.error('Failed to update template');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveAsNew = (name: string, isPublic: boolean, category: string) => {
    saveDraftAsTemplate(name, isPublic, category);
  };

  const saveDraftAsTemplate = async (name: string, isPublic: boolean, category: string) => {
    try {
      setIsLoading(true);
      const request: ChecklistTemplateRequest = {
        name,
        content: checklist,
        category,
        is_public: isPublic,
      };

      const newTemplate = await apiClient.createChecklistTemplate(request);
      
      // Track ownership for anonymous users
      updateOwnedTemplates(newTemplate.id);
      
      toast.success('Template saved successfully!');
      await loadTemplates(); // Refresh templates
      
      // Select the newly created template
      setSelectedTemplateId(newTemplate.id);
      setSelectedTemplate(newTemplate);
    } catch (error) {
      console.error('Error saving template:', error);
      toast.error('Failed to save template');
    } finally {
      setIsLoading(false);
    }
  };

  // Check if current template can be updated
  const canUpdateCurrent = selectedTemplate && (selectedTemplate.is_owner || ownedTemplates.has(selectedTemplate.id));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Select a checklist template
        </label>
        <Select value={selectedTemplateId} onValueChange={handleTemplateSelect} disabled={loadingTemplates}>
          <SelectTrigger className="bg-input">
            <SelectValue placeholder={loadingTemplates ? "Loading templates..." : "Choose a checklist template"} />
          </SelectTrigger>
          <SelectContent>
            {templates.map((template) => (
              <SelectItem key={template.id} value={template.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{template.name}</span>
                  <div className="flex gap-1 ml-2">
                    {template.is_public && (
                      <span className="text-xs bg-green-100 text-green-800 px-1 rounded">Public</span>
                    )}
                    {(template.is_owner || ownedTemplates.has(template.id)) && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-1 rounded">Yours</span>
                    )}
                  </div>
                </div>
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
        {canUpdateCurrent && (
          <Button 
            variant="outline" 
            onClick={handleSaveChanges}
            disabled={isLoading}
          >
            Save Changes
          </Button>
        )}
        <Button 
          variant="outline" 
          onClick={() => setSaveDialogOpen(true)}
          disabled={isLoading || !checklist.trim()}
        >
          Save as New
        </Button>
      </div>

      <SaveTemplateDialog
        isOpen={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        onSave={handleSaveAsNew}
        defaultName={selectedTemplate ? `${selectedTemplate.name} (Copy)` : ''}
      />
    </div>
  );
}