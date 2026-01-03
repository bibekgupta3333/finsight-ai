import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { parse } from 'papaparse';
import type { FraudAnalysisResult } from './validations';

/**
 * Export analysis results to CSV format
 */
export function exportToCSV(
  results: FraudAnalysisResult[],
  filename: string = 'fraud-analysis-results.csv'
) {
  const headers = [
    'Transaction ID',
    'Is Fraud',
    'Confidence',
    'Risk Score',
    'Decision',
    'Reasoning',
    'Timestamp',
  ];

  const rows = results.map((result, index) => [
    `TXN-${String(index + 1).padStart(3, '0')}`,
    result.is_fraud ? 'Yes' : 'No',
    (result.confidence * 100).toFixed(2) + '%',
    result.risk_score.toFixed(2),
    result.decision,
    result.reasoning.replace(/,/g, ';'), // Replace commas to avoid CSV issues
    result.timestamp || new Date().toISOString(),
  ]);

  const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

/**
 * Export analysis results to PDF format
 */
export function exportToPDF(
  results: FraudAnalysisResult[],
  filename: string = 'fraud-analysis-report.pdf'
) {
  const doc = new jsPDF();

  // Add title
  doc.setFontSize(18);
  doc.text('Fraud Detection Analysis Report', 14, 22);

  // Add metadata
  doc.setFontSize(10);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 30);
  doc.text(`Total Transactions: ${results.length}`, 14, 36);

  const fraudCount = results.filter((r) => r.is_fraud).length;
  doc.text(`Fraud Detected: ${fraudCount} (${((fraudCount / results.length) * 100).toFixed(2)}%)`, 14, 42);

  // Create table data
  const tableData = results.map((result, index) => [
    `TXN-${String(index + 1).padStart(3, '0')}`,
    result.is_fraud ? 'Yes' : 'No',
    `${(result.confidence * 100).toFixed(2)}%`,
    result.risk_score.toFixed(2),
    result.decision,
    result.reasoning.substring(0, 50) + (result.reasoning.length > 50 ? '...' : ''),
  ]);

  // Add table
  autoTable(doc, {
    head: [['ID', 'Fraud', 'Confidence', 'Risk', 'Decision', 'Reasoning']],
    body: tableData,
    startY: 50,
    styles: { fontSize: 8 },
    headStyles: { fillColor: [59, 130, 246] },
  });

  // Save PDF
  doc.save(filename);
}

/**
 * Parse CSV file to transaction objects
 */
export function parseCSVFile(file: File): Promise<any[]> {
  return new Promise((resolve, reject) => {
    parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        resolve(results.data);
      },
      error: (error) => {
        reject(error);
      },
    });
  });
}

/**
 * Format number as currency
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Format date/time
 */
export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

/**
 * Download data as JSON
 */
export function downloadJSON(data: any, filename: string = 'data.json') {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
