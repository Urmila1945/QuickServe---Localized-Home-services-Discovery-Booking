import React, { useState } from 'react';

interface ARPreviewProps {
  sessionId: string;
  problems: Array<{
    id: string;
    type: string;
    category: string;
    estimated_cost: number;
    severity: string;
  }>;
  onProblemSelect: (problemId: string) => void;
}

export default function ARPreview({ sessionId, problems, onProblemSelect }: ARPreviewProps) {
  const [selectedProblem, setSelectedProblem] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'overview' | 'detail' | 'simulation'>('overview');

  const handleProblemClick = (problemId: string) => {
    setSelectedProblem(problemId);
    onProblemSelect(problemId);
    setViewMode('detail');
  };

  return (
    <div className="w-full h-96 bg-gray-900 rounded-lg overflow-hidden relative">
      <div className="absolute top-4 left-4 z-10 flex space-x-2">
        <button
          onClick={() => setViewMode('overview')}
          className={`px-3 py-1 rounded text-sm ${viewMode === 'overview' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
            }`}
        >
          Overview
        </button>
        <button
          onClick={() => setViewMode('detail')}
          className={`px-3 py-1 rounded text-sm ${viewMode === 'detail' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
            }`}
          disabled={!selectedProblem}
        >
          Detail
        </button>
      </div>

      <div className="p-8 text-white">
        <h3 className="text-xl font-bold mb-4">AR Problem Detection</h3>
        <div className="grid grid-cols-2 gap-4">
          {problems.map((problem) => (
            <div
              key={problem.id}
              onClick={() => handleProblemClick(problem.id)}
              className={`p-4 rounded-lg cursor-pointer transition-all ${selectedProblem === problem.id
                  ? 'bg-blue-600 ring-2 ring-blue-400'
                  : 'bg-gray-800 hover:bg-gray-700'
                }`}
            >
              <h4 className="font-semibold">{problem.category}</h4>
              <p className="text-sm opacity-75">Severity: {problem.severity}</p>
              <p className="text-lg font-bold">${problem.estimated_cost}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}