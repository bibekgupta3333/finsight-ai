'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { transactionSchema, type Transaction } from '@/lib/validations';
import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

// Form schema extends transaction schema with optional isFraud fields
const transactionFormSchema = transactionSchema.extend({
  isFraud: z.number().int().min(0).max(1).optional(),
  isFlaggedFraud: z.number().int().min(0).max(1).optional(),
});

type TransactionFormData = z.infer<typeof transactionFormSchema>;

interface TransactionFormProps {
  onSubmit: (data: Transaction) => void | Promise<void>;
  isSubmitting?: boolean;
  defaultValues?: Partial<TransactionFormData>;
}

export function TransactionForm({ onSubmit, isSubmitting, defaultValues }: TransactionFormProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 3;

  const {
    register,
    handleSubmit,
    formState: { errors },
    trigger,
  } = useForm<TransactionFormData>({
    resolver: zodResolver(transactionFormSchema),
    defaultValues: {
      step: 1,
      type: 'PAYMENT',
      amount: 0,
      nameOrig: '',
      oldbalanceOrg: 0,
      newbalanceOrig: 0,
      nameDest: '',
      oldbalanceDest: 0,
      newbalanceDest: 0,
      isFraud: 0,
      isFlaggedFraud: 0,
      ...defaultValues,
    },
  });

  const nextStep = async () => {
    const fieldsToValidate = getFieldsForStep(currentStep);
    const isValid = await trigger(fieldsToValidate);
    if (isValid && currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const getFieldsForStep = (step: number): (keyof TransactionFormData)[] => {
    switch (step) {
      case 1:
        return ['step', 'type', 'amount'];
      case 2:
        return ['nameOrig', 'oldbalanceOrg', 'newbalanceOrig'];
      case 3:
        return ['nameDest', 'oldbalanceDest', 'newbalanceDest'];
      default:
        return [];
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transaction Details</CardTitle>
        <CardDescription>
          Step {currentStep} of {totalSteps} - Enter transaction information
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Step 1: Basic Info */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="step">Transaction Step</Label>
                <Input
                  id="step"
                  type="number"
                  {...register('step', { valueAsNumber: true })}
                  placeholder="1"
                />
                {errors.step && (
                  <p className="text-sm text-red-500 mt-1">{errors.step.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="type">Transaction Type</Label>
                <select
                  id="type"
                  {...register('type')}
                  className="w-full px-3 py-2 border border-zinc-300 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-900"
                >
                  <option value="PAYMENT">PAYMENT</option>
                  <option value="TRANSFER">TRANSFER</option>
                  <option value="CASH_OUT">CASH_OUT</option>
                  <option value="DEBIT">DEBIT</option>
                  <option value="CASH_IN">CASH_IN</option>
                </select>
                {errors.type && <p className="text-sm text-red-500 mt-1">{errors.type.message}</p>}
              </div>

              <div>
                <Label htmlFor="amount">Amount</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  {...register('amount', { valueAsNumber: true })}
                  placeholder="1000.00"
                />
                {errors.amount && (
                  <p className="text-sm text-red-500 mt-1">{errors.amount.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Origin Account */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="nameOrig">Origin Account</Label>
                <Input
                  id="nameOrig"
                  type="text"
                  {...register('nameOrig')}
                  placeholder="C1234567890"
                />
                {errors.nameOrig && (
                  <p className="text-sm text-red-500 mt-1">{errors.nameOrig.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="oldbalanceOrg">Old Balance (Origin)</Label>
                <Input
                  id="oldbalanceOrg"
                  type="number"
                  step="0.01"
                  {...register('oldbalanceOrg', { valueAsNumber: true })}
                  placeholder="5000.00"
                />
                {errors.oldbalanceOrg && (
                  <p className="text-sm text-red-500 mt-1">{errors.oldbalanceOrg.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="newbalanceOrig">New Balance (Origin)</Label>
                <Input
                  id="newbalanceOrig"
                  type="number"
                  step="0.01"
                  {...register('newbalanceOrig', { valueAsNumber: true })}
                  placeholder="4000.00"
                />
                {errors.newbalanceOrig && (
                  <p className="text-sm text-red-500 mt-1">{errors.newbalanceOrig.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Destination Account */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="nameDest">Destination Account</Label>
                <Input
                  id="nameDest"
                  type="text"
                  {...register('nameDest')}
                  placeholder="M9876543210"
                />
                {errors.nameDest && (
                  <p className="text-sm text-red-500 mt-1">{errors.nameDest.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="oldbalanceDest">Old Balance (Destination)</Label>
                <Input
                  id="oldbalanceDest"
                  type="number"
                  step="0.01"
                  {...register('oldbalanceDest', { valueAsNumber: true })}
                  placeholder="0.00"
                />
                {errors.oldbalanceDest && (
                  <p className="text-sm text-red-500 mt-1">{errors.oldbalanceDest.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="newbalanceDest">New Balance (Destination)</Label>
                <Input
                  id="newbalanceDest"
                  type="number"
                  step="0.01"
                  {...register('newbalanceDest', { valueAsNumber: true })}
                  placeholder="1000.00"
                />
                {errors.newbalanceDest && (
                  <p className="text-sm text-red-500 mt-1">{errors.newbalanceDest.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-4">
            {currentStep > 1 ? (
              <Button type="button" variant="outline" onClick={prevStep}>
                Previous
              </Button>
            ) : (
              <div />
            )}

            {currentStep < totalSteps ? (
              <Button type="button" onClick={nextStep}>
                Next
              </Button>
            ) : (
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Analyzing...' : 'Analyze Transaction'}
              </Button>
            )}
          </div>

          {/* Progress Indicator */}
          <div className="flex justify-center gap-2 pt-4">
            {[1, 2, 3].map((step) => (
              <div
                key={step}
                className={`h-2 w-12 rounded-full ${
                  step === currentStep
                    ? 'bg-blue-500'
                    : step < currentStep
                    ? 'bg-green-500'
                    : 'bg-zinc-300 dark:bg-zinc-700'
                }`}
              />
            ))}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
