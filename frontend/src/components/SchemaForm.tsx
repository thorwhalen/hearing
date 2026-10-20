// A form generated from a zodal collection: one field per schema field, each
// drawn by the component the @zodal/ui-shadcn renderer registry picks for it
// (a select for an enum, a checkbox for a boolean, a text input for a string…).
//
// For a frontend novice: nothing here knows about any particular setting. The
// schema (see settings.ts) decides which fields exist, their labels, help texts
// and options; `toFormConfig` turns it into field configs; the registry maps
// each field to a component. `adjust` lets the caller change a field's config
// from the current values (disable one, relabel options) without a hand-built
// control. A new field in the schema appears here with no change to this file.
import { useMemo } from 'react';
import { toFormConfig, type FormFieldConfig } from '@zodal/ui';
import { createShadcnRegistry } from '@zodal/ui-shadcn';

const registry = createShadcnRegistry();

// The parts of a zodal collection this form reads (defineCollection's result).
interface FormCollection {
  fieldAffordances: Record<string, unknown>;
}

interface Props<T extends Record<string, unknown>> {
  collection: FormCollection;
  value: T;
  onChange: (next: T) => void;
  adjust?: (config: FormFieldConfig, value: T) => FormFieldConfig;
}

export function SchemaForm<T extends Record<string, unknown>>({ collection, value, onChange, adjust }: Props<T>) {
  const configs = useMemo(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- zodal's generic is the schema type
    () => toFormConfig(collection as any, 'edit').filter((c) => !c.hidden).sort((a, b) => a.order - b.order),
    [collection],
  );
  return (
    <div className="schema-form">
      {configs.map((base) => {
        const config = adjust ? adjust(base, value) : base;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- the registry takes a resolved affordance
        const Field = registry.resolve(collection.fieldAffordances[base.name] as any, { mode: 'form' } as any);
        if (!Field) return null;
        return (
          <div className="schema-field" key={base.name} data-field={base.name}>
            <Field
              config={config}
              field={{ value: value[base.name], onChange: (next: unknown) => onChange({ ...value, [base.name]: next }) }}
            />
          </div>
        );
      })}
    </div>
  );
}
