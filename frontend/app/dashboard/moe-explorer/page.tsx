import { MoEArchitectureViz } from '@/components/moe/MoEArchitectureViz';
import { CostComparison } from '@/components/moe/CostComparison';
import { ExpertActivationHeatmap } from '@/components/moe/ExpertActivationHeatmap';

export default function MoEExplorerPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Mixture of Experts (MoE) Cost Explorer</h1>
        <p className="text-muted-foreground mt-2">
          Analyze MoE architecture efficiency, cost savings, and expert activation patterns
        </p>
      </div>

      <div className="grid gap-6">
        {/* Row 1: Architecture Visualization */}
        <MoEArchitectureViz />

        {/* Row 2: Cost Comparison + Expert Activation */}
        <div className="grid gap-6 lg:grid-cols-2">
          <CostComparison />
          <ExpertActivationHeatmap />
        </div>
      </div>
    </div>
  );
}
