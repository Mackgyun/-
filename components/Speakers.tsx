import React from 'react';
import { SPEAKERS } from '../constants';
import { User } from 'lucide-react';
import { Speaker } from '../types';

const SpeakerCard: React.FC<{ speaker: Speaker }> = ({ speaker }) => {
  // Helper function to determine font size based on topic length
  const getTopicSizeClass = (text: string) => {
    if (text.length > 35) return "text-[11px] tracking-tight";
    if (text.length > 25) return "text-xs tracking-tight";
    return "text-sm";
  };

  return (
    <div 
      className="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 overflow-hidden flex flex-col h-full"
    >
      {/* Topic moved to top, above image */}
      {speaker.topic && (
        <div className="bg-slate-50 px-3 py-3 border-b border-slate-100 flex items-center justify-center min-h-[3rem]">
          <p className={`${getTopicSizeClass(speaker.topic)} font-bold text-slate-800 whitespace-nowrap overflow-hidden text-ellipsis w-full text-center`}>
            {speaker.topic}
          </p>
        </div>
      )}

      {/* Speaker Image Header */}
      <div className="aspect-[4/3] w-full overflow-hidden relative bg-slate-100 flex-shrink-0">
        {speaker.imageUrl ? (
          <>
            <img 
              src={speaker.imageUrl} 
              alt={speaker.name}
              loading="lazy"
              className="w-full h-full object-cover object-top transition-transform duration-700 group-hover:scale-105"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                const fallback = e.currentTarget.parentElement?.querySelector('.fallback-icon');
                if (fallback) fallback.classList.remove('hidden');
              }}
            />
            <div className="fallback-icon hidden absolute inset-0 flex items-center justify-center bg-slate-100 text-slate-300">
              <User className="w-16 h-16 opacity-20" />
            </div>
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-slate-100 text-slate-300">
            <User className="w-16 h-16 opacity-20" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent opacity-90" />
        
        <div className="absolute bottom-0 left-0 p-4 text-white z-10 w-full">
          <div className="flex flex-col">
            <h3 className="text-xl font-bold leading-none mb-1">{speaker.name}</h3>
          </div>
        </div>
      </div>

      <div className="p-5 flex flex-col flex-grow">
        <div className="mb-3">
          <p className="text-xs font-bold text-blue-600 leading-snug break-keep">
            {speaker.role}
          </p>
        </div>
        
        <div className="relative flex-grow">
          <p className="text-slate-600 text-xs leading-relaxed break-keep">
            {speaker.bio}
          </p>
        </div>
      </div>
    </div>
  );
};

export const Speakers: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {SPEAKERS.map((speaker) => (
        <SpeakerCard key={speaker.id} speaker={speaker} />
      ))}
    </div>
  );
};