import React from 'react';
import { SPEAKERS } from '../constants';
import { User } from 'lucide-react';

export const Speakers: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {SPEAKERS.map((speaker) => (
        <div 
          key={speaker.id} 
          className="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 overflow-hidden flex flex-col"
        >
          {/* Speaker Image Header */}
          <div className="aspect-[3/2] w-full overflow-hidden relative bg-slate-100">
            {speaker.imageUrl ? (
              <>
                <img 
                  src={speaker.imageUrl} 
                  alt={speaker.name}
                  loading="lazy"
                  className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                    const fallback = e.currentTarget.parentElement?.querySelector('.fallback-icon');
                    if (fallback) fallback.classList.remove('hidden');
                  }}
                />
                <div className="fallback-icon hidden absolute inset-0 flex items-center justify-center bg-slate-100 text-slate-300">
                  <User className="w-20 h-20 opacity-20" />
                </div>
              </>
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-slate-100 text-slate-300">
                <User className="w-20 h-20 opacity-20" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-90" />
            
            <div className="absolute bottom-0 left-0 p-6 text-white z-10">
              <div className="flex items-end gap-3">
                <h3 className="text-2xl font-bold leading-none">{speaker.name}</h3>
                <p className="text-sm text-slate-300 font-medium mb-0.5 line-clamp-1">{speaker.role.split(' / ')[0]}</p>
              </div>
            </div>
          </div>

          <div className="p-6 flex flex-col flex-grow">
            <div className="mb-4">
              <p className="text-sm font-medium text-blue-600 leading-snug">
                {speaker.role}
              </p>
            </div>
            
            <p className="text-slate-600 text-sm leading-relaxed flex-grow whitespace-pre-wrap">
              {speaker.bio}
            </p>

            {speaker.topic && (
              <div className="mt-6 pt-4 border-t border-slate-100">
                <p className="text-xs text-slate-400 uppercase font-bold mb-1">Topic</p>
                <p className="text-base font-semibold text-slate-800">
                  {speaker.topic}
                </p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};