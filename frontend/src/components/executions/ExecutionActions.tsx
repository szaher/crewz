'use client';

import { useState } from 'react';

interface ExecutionActionsProps {
  executionId: string;
  status: string;
  onActionComplete?: () => void;
}

/**
 * ExecutionActions Component (T047)
 *
 * Action buttons for execution management.
 * - Cancel button with confirmation modal (shown for running/queued executions)
 * - Re-execute button (shown for completed/failed/cancelled executions)
 * - Conditionally shown based on execution status
 * - Handles API calls for cancel and re-execute
 */
export default function ExecutionActions({
  executionId,
  status,
  onActionComplete
}: ExecutionActionsProps) {
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isReExecuting, setIsReExecuting] = useState(false);

  // Determine which actions are available based on status
  const canCancel = ['running', 'queued', 'pending'].includes(status.toLowerCase());
  const canReExecute = ['completed', 'failed', 'cancelled'].includes(status.toLowerCase());

  // Handle cancel execution
  const handleCancel = async () => {
    try {
      setIsCancelling(true);

      const token = localStorage.getItem('token') || '';
      const response = await fetch(
        `http://localhost:8000/api/v1/executions/${executionId}/cancel`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to cancel execution');
      }

      const result = await response.json();

      // Close modal
      setShowCancelModal(false);

      // Show success message
      alert('Execution cancelled successfully');

      // Notify parent
      if (onActionComplete) {
        onActionComplete();
      }

    } catch (err) {
      console.error('[ExecutionActions] Cancel failed:', err);
      alert('Failed to cancel execution. Please try again.');
    } finally {
      setIsCancelling(false);
    }
  };

  // Handle re-execute
  const handleReExecute = async () => {
    try {
      setIsReExecuting(true);

      const token = localStorage.getItem('token') || '';
      const response = await fetch(
        `http://localhost:8000/api/v1/executions/${executionId}/re-execute`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to re-execute');
      }

      const result = await response.json();
      const newJobId = result.new_job_id;

      // Redirect to new execution
      window.location.href = `/executions/${newJobId}`;

    } catch (err) {
      console.error('[ExecutionActions] Re-execute failed:', err);
      alert('Failed to re-execute. Please try again.');
      setIsReExecuting(false);
    }
  };

  // Don't render if no actions available
  if (!canCancel && !canReExecute) {
    return null;
  }

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-gray-900">Execution Actions</h3>
            <p className="text-xs text-gray-500 mt-1">Manage this execution</p>
          </div>

          <div className="flex items-center space-x-2">
            {/* Cancel Button */}
            {canCancel && (
              <button
                onClick={() => setShowCancelModal(true)}
                disabled={isCancelling}
                className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                {isCancelling ? 'Cancelling...' : 'Cancel Execution'}
              </button>
            )}

            {/* Re-execute Button */}
            {canReExecute && (
              <button
                onClick={handleReExecute}
                disabled={isReExecuting}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isReExecuting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1.5"></div>
                    Re-executing...
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Re-execute
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
              onClick={() => setShowCancelModal(false)}
            />

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <div className="sm:flex sm:items-start">
                {/* Icon */}
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                  <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>

                {/* Content */}
                <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 className="text-lg leading-6 font-medium text-gray-900">
                    Cancel Execution
                  </h3>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500">
                      Are you sure you want to cancel this execution? This action cannot be undone.
                      The execution will be stopped immediately and marked as cancelled.
                    </p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={isCancelling}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCancelling ? 'Cancelling...' : 'Yes, Cancel Execution'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCancelModal(false)}
                  disabled={isCancelling}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  No, Keep Running
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
