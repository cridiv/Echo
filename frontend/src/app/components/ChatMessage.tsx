// components/ChatMessage.tsx
import { format } from 'date-fns';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  type: 'text' | 'file' | 'audio';
  fileName?: string;
  fileSize?: number;
  audioDuration?: number;
}

interface ChatMessageProps {
  message: Message;
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
        isUser 
          ? 'bg-blue-600 text-white' 
          : 'bg-gray-800 text-gray-100'
      }`}>
        {/* Message Content */}
        {message.type === 'text' && (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}

        {message.type === 'file' && (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium">{message.fileName}</span>
            </div>
            {message.fileSize && (
              <p className="text-xs opacity-70">{formatFileSize(message.fileSize)}</p>
            )}
          </div>
        )}

        {message.type === 'audio' && (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <span className="text-sm font-medium">Voice Message</span>
            </div>
            {message.audioDuration && (
              <p className="text-xs opacity-70">{formatDuration(message.audioDuration)}</p>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className={`text-xs mt-1 ${
          isUser ? 'text-blue-200' : 'text-gray-500'
        }`}>
          {format(message.timestamp, 'HH:mm')}
        </p>
      </div>
    </div>
  );
}