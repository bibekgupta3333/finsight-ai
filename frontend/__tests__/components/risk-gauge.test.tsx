import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskGauge } from '@/components/fraud/risk-gauge';

describe('RiskGauge', () => {
  it('should render with default size', () => {
    render(<RiskGauge value={50} />);
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });

  it('should display LOW risk for values 0-25', () => {
    render(<RiskGauge value={20} />);
    expect(screen.getByText('LOW')).toBeInTheDocument();
  });

  it('should display MEDIUM risk for values 25-50', () => {
    render(<RiskGauge value={40} />);
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });

  it('should display HIGH risk for values 50-75', () => {
    render(<RiskGauge value={60} />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });

  it('should display CRITICAL risk for values 75-100', () => {
    render(<RiskGauge value={85} />);
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
  });

  it('should hide label when showLabel is false', () => {
    render(<RiskGauge value={50} showLabel={false} />);
    expect(screen.queryByText('MEDIUM')).not.toBeInTheDocument();
  });

  it('should apply correct color classes based on risk level', () => {
    const { container, rerender } = render(<RiskGauge value={20} />);
    expect(container.querySelector('.bg-green-500')).toBeInTheDocument();

    rerender(<RiskGauge value={40} />);
    expect(container.querySelector('.bg-yellow-500')).toBeInTheDocument();

    rerender(<RiskGauge value={60} />);
    expect(container.querySelector('.bg-orange-500')).toBeInTheDocument();

    rerender(<RiskGauge value={85} />);
    expect(container.querySelector('.bg-red-500')).toBeInTheDocument();
  });

  it('should render different sizes correctly', () => {
    const { container, rerender } = render(<RiskGauge value={50} size="sm" />);
    expect(container.querySelector('.h-2')).toBeInTheDocument();

    rerender(<RiskGauge value={50} size="md" />);
    expect(container.querySelector('.h-3')).toBeInTheDocument();

    rerender(<RiskGauge value={50} size="lg" />);
    expect(container.querySelector('.h-4')).toBeInTheDocument();
  });
});
