import React, { useState } from 'react';
import { FileText, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp, Activity, Receipt, File } from 'lucide-react';

interface ExtractedData {
    [key: string]: any;
}

interface DocumentCardProps {
    filename: string;
    type: string;
    status: string;
    extractedData?: ExtractedData;
    confidence?: number;
}

const getIcon = (type: string) => {
    switch (type.toLowerCase()) {
        case 'prescription': return <Activity className="w-5 h-5 text-brand-500" />;
        case 'bill': return <Receipt className="w-5 h-5 text-emerald-500" />;
        case 'report': return <FileText className="w-5 h-5 text-blue-500" />;
        default: return <File className="w-5 h-5 text-indigo-400" />;
    }
};

const StatusBadge = ({ status }: { status: string }) => {
    switch (status) {
        case 'processed':
            return (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-100">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Processed
                </span>
            );
        case 'processing':
            return (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold border border-brand-100 animate-pulse">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Processing
                </span>
            );
        case 'failed':
            return (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 text-red-700 text-xs font-semibold border border-red-100">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Failed
                </span>
            );
        default:
            return (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold border border-slate-200">
                    <Loader2 className="w-3.5 h-3.5" />
                    Queueing
                </span>
            );
    }
};

export default function DocumentCard({ filename, type, status, extractedData, confidence }: DocumentCardProps) {
    const [showRaw, setShowRaw] = useState(false);

    // Helper to extract key fields based on doc type for the summary view
    const getSummaryFields = () => {
        if (!extractedData) return [];

        const fields = [];
        if (extractedData.patient_name || extractedData.patient?.name)
            fields.push({ label: 'Patient', value: extractedData.patient_name || extractedData.patient?.name });

        if (extractedData.total_amount || extractedData.amount || extractedData.bill?.total_amount)
            fields.push({ label: 'Amount', value: `₹${extractedData.total_amount || extractedData.amount || extractedData.bill?.total_amount}` });

        if (extractedData.doctor_name || extractedData.doctor?.name)
            fields.push({ label: 'Doctor', value: extractedData.doctor_name || extractedData.doctor?.name });

        if (extractedData.date || extractedData.bill_date)
            fields.push({ label: 'Date', value: extractedData.date || extractedData.bill_date });

        return fields;
    };

    const summaryFields = getSummaryFields();

    return (
        <div className="group relative bg-white/80 backdrop-blur-md rounded-xl border border-white/40 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1 overflow-hidden">
            {/* Decorative gradient blob */}
            <div className="absolute -right-10 -top-10 w-24 h-24 bg-gradient-to-br from-brand-100 to-transparent rounded-full opacity-50 blur-xl group-hover:opacity-100 transition-opacity"></div>

            <div className="p-5 relative z-10">
                {/* Header */}
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-lg bg-surface-50 border border-slate-100`}>
                            {getIcon(type)}
                        </div>
                        <div>
                            <h3 className="font-semibold text-slate-800 text-sm truncate max-w-[180px]" title={filename}>
                                {filename}
                            </h3>
                            <p className="text-xs text-slate-500 uppercase tracking-wider font-medium mt-0.5">
                                {type}
                            </p>
                        </div>
                    </div>
                    <StatusBadge status={status} />
                </div>

                {/* Content Area */}
                {status === 'processed' && (
                    <div className="mt-4">
                        {summaryFields.length > 0 ? (
                            <div className="grid grid-cols-2 gap-3 mb-4">
                                {summaryFields.map((field, idx) => (
                                    <div key={idx} className="bg-surface-50 p-2 rounded-lg border border-slate-100">
                                        <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">{field.label}</p>
                                        <p className="text-sm font-semibold text-slate-700 truncate">{field.value}</p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-sm text-slate-500 italic mb-4">
                                Processing complete. No key fields identified.
                            </div>
                        )}

                        {/* Confidence Bar */}
                        {confidence && (
                            <div className="space-y-1.5 mb-4">
                                <div className="flex justify-between text-xs">
                                    <span className="text-slate-500 font-medium">AI Confidence</span>
                                    <span className={`font-bold ${confidence > 0.8 ? 'text-emerald-600' : 'text-amber-600'}`}>
                                        {(confidence * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-1000 ${confidence > 0.8 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                                        style={{ width: `${confidence * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        )}

                        {/* Raw Data Toggle */}
                        <div className="border-t border-slate-100 pt-3">
                            <button
                                onClick={() => setShowRaw(!showRaw)}
                                className="flex items-center gap-1 text-xs text-brand-600 font-medium hover:text-brand-700 hover:underline transition-colors w-full justify-center"
                            >
                                {showRaw ? 'Hide Raw Data' : 'View Source Data'}
                                {showRaw ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>

                            {showRaw && (
                                <div className="mt-3 p-3 bg-slate-900 rounded-lg overflow-hidden animate-slide-up">
                                    <div className="flex justify-between items-center mb-2 border-b border-slate-800 pb-2">
                                        <span className="text-[10px] text-slate-400 font-mono">JSON Source</span>
                                    </div>
                                    <pre className="text-[10px] font-mono text-emerald-400 overflow-auto max-h-40 custom-scrollbar">
                                        {JSON.stringify(extractedData, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
