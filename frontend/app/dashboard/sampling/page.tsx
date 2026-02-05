import { SamplingConfigurator } from '@/components/sampling/SamplingConfigurator';
import { TemperatureScheduleChart } from '@/components/sampling/TemperatureScheduleChart';
import { ParameterComparison } from '@/components/sampling/ParameterComparison';

export default function SamplingOptimizerPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Sampling Optimizer</h1>
        <p className="text-muted-foreground mt-2">
          Fine-tune sampling parameters with AI-powered recommendations and visualize temperature schedules
        </p>
      </div>

      <div className="grid gap-6">
        {/* Row 1: Sampling Configurator (full width) */}
        <SamplingConfigurator />

        {/* Row 2: Temperature Schedule + Parameter Comparison */}
        <div className="grid gap-6 lg:grid-cols-2">
          <TemperatureScheduleChart />
          <ParameterComparison />
        </div>
      </div>
    </div>
  );
}
