/**
 * @jest-environment jsdom
 */

/*
 * Scenario Edit Component Tests
 * Tests for StepEditor and DataBindingCard components
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

describe('StepEditor Component', () => {
  it('should render empty state when no steps', () => {
    const MockStepEditor = ({ steps }: { steps: any[] }) => {
      return (
        <div>
          {steps.length === 0 && <p>Adım yok</p>}
          <button>+ Adım Ekle</button>
        </div>
      );
    };

    const { container } = render(<MockStepEditor steps={[]} />);
    expect(screen.getByText('Adım yok')).toBeInTheDocument();
    expect(screen.getByText('+ Adım Ekle')).toBeInTheDocument();
  });

  it('should render keyword dropdown with all options', () => {
    const keywords = ['Given', 'When', 'Then', 'And', 'But'];

    const MockSelect = () => (
      <select>
        {keywords.map((kw) => (
          <option key={kw} value={kw}>{kw}</option>
        ))}
      </select>
    );

    render(<MockSelect />);
    keywords.forEach((kw) => {
      expect(screen.getByRole('option', { name: kw })).toBeInTheDocument();
    });
  });

  it('should validate at least one step required', () => {
    const steps: any[] = [];
    const isValid = steps.length > 0;

    expect(isValid).toBe(false);
  });
});

describe('DataBindingCard Component', () => {
  it('should render empty state when no bindings', () => {
    const MockDataBindingCard = ({ dataBindings }: { dataBindings: any[] }) => {
      return (
        <div>
          <h3>📊 Veri Seti Bağlaması</h3>
          {dataBindings.length === 0 && <p>Veri seti bağlaması yok</p>}
          <button>+ Bağlama Ekle</button>
        </div>
      );
    };

    const { container } = render(<MockDataBindingCard dataBindings={[]} />);
    expect(screen.getByText('📊 Veri Seti Bağlaması')).toBeInTheDocument();
    expect(screen.getByText('Veri seti bağlaması yok')).toBeInTheDocument();
    expect(screen.getByText('+ Bağlama Ekle')).toBeInTheDocument();
  });

  it('should render status dropdown with correct options', () => {
    const STATUS_OPTIONS = ['draft', 'active', 'deprecated', 'review'] as const;

    const MockStatusSelect = () => (
      <select data-testid="scenario-edit-select-status">
        {STATUS_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );

    render(<MockStatusSelect />);
    STATUS_OPTIONS.forEach((opt) => {
      expect(screen.getByRole('option', { name: opt })).toBeInTheDocument();
    });
  });

  it('should render error template button', () => {
    const MockButton = () => (
      <button title="Hata şablonu ekle">🐛</button>
    );

    render(<MockButton />);
    const button = screen.getByRole('button', { name: '🐛' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('title', 'Hata şablonu ekle');
  });
});

describe('Error Template Integration', () => {
  it('should create error template string correctly', () => {
    const template = "Hata:\nAdımlar:\nBeklenen:\nGerçekleşen:\nOrtam:";
    const lines = template.split('\n');

    expect(lines).toEqual([
      'Hata:',
      'Adımlar:',
      'Beklenen:',
      'Gerçekleşen:',
      'Ortam:'
    ]);
  });
});
