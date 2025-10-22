'use client';

import { useState } from 'react';
import { getApiBaseUrl } from '@/lib/api-url';

interface Artifact {
  artifact_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  artifact_type: string;
  version: number;
  download_url: string;
}

interface ArtifactListProps {
  executionId: string;
  artifacts?: Artifact[];
}

/**
 * ArtifactList Component (T046)
 *
 * Displays execution artifacts with download functionality.
 * - Table showing file_name, size, type, version
 * - Download button for each artifact
 * - Version dropdown (if multiple versions exist)
 * - Hidden if no artifacts available
 * - Formats file sizes in human-readable format
 */
export default function ArtifactList({ executionId, artifacts = [] }: ArtifactListProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  // Get artifact type badge color
  const getTypeBadgeColor = (type: string): string => {
    switch (type.toLowerCase()) {
      case 'output':
        return 'bg-blue-100 text-blue-800';
      case 'log':
        return 'bg-gray-100 text-gray-800';
      case 'result':
        return 'bg-green-100 text-green-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-purple-100 text-purple-800';
    }
  };

  // Download artifact
  const handleDownload = async (artifact: Artifact) => {
    try {
      setDownloadingId(artifact.artifact_id);

      const token = localStorage.getItem('token') || '';

      // Get presigned download URL from API
      const response = await fetch(
        `${getApiBaseUrl()}/api/v1/artifacts/${artifact.artifact_id}/download`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to get download URL');
      }

      const data = await response.json();
      const downloadUrl = data.download_url;

      // Trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = artifact.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

    } catch (err) {
      console.error('[ArtifactList] Download failed:', err);
      alert('Failed to download artifact. Please try again.');
    } finally {
      setDownloadingId(null);
    }
  };

  // Don't render if no artifacts
  if (!artifacts || artifacts.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <h3 className="text-sm font-medium text-gray-900">Execution Artifacts</h3>
          <span className="bg-gray-200 text-gray-700 text-xs px-2 py-0.5 rounded-full">
            {artifacts.length}
          </span>
        </div>
      </div>

      {/* Artifacts Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                File Name
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Size
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Version
              </th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {artifacts.map((artifact) => (
              <tr key={artifact.artifact_id} className="hover:bg-gray-50">
                {/* File Name */}
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm text-gray-900 font-medium">{artifact.file_name}</span>
                  </div>
                </td>

                {/* Type */}
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getTypeBadgeColor(artifact.artifact_type)}`}>
                    {artifact.artifact_type}
                  </span>
                </td>

                {/* Size */}
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                  {formatFileSize(artifact.file_size)}
                </td>

                {/* Version */}
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-700">
                    v{artifact.version}
                  </span>
                </td>

                {/* Actions */}
                <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => handleDownload(artifact)}
                    disabled={downloadingId === artifact.artifact_id}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {downloadingId === artifact.artifact_id ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1.5"></div>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <svg className="h-3 w-3 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </>
                    )}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-3">
        <p className="text-xs text-gray-500">
          Artifacts are stored for 30 days from execution completion.
        </p>
      </div>
    </div>
  );
}
