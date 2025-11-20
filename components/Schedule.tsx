import React from 'react';
import { SCHEDULE } from '../constants';
import { Clock, MapPin } from 'lucide-react';

export const Schedule: React.FC = () => {
  return (
    <div className="space-y-12">
      {SCHEDULE.map((day, dayIdx) => (
        <div key={dayIdx} className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
          {/* Header for the day */}
          <div className="bg-slate-50 px-6 py-5 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <h3 className="text-xl font-bold text-blue-900 flex items-center gap-2">
              <span className="bg-blue-600 text-white text-xs px-2 py-1 rounded">DAY {dayIdx + 1}</span>
              {day.date}
            </h3>
            <div className="flex items-center text-slate-500 text-sm">
              <MapPin className="h-4 w-4 mr-1" />
              {day.location}
            </div>
          </div>

          {/* Timeline items */}
          <div className="p-6 sm:p-8">
            <div className="relative border-l-2 border-blue-100 ml-3 sm:ml-6 space-y-8">
              {day.items.map((item, idx) => (
                <div key={idx} className="relative pl-8 sm:pl-10 group">
                  {/* Timeline Dot */}
                  <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-white border-4 border-blue-200 group-hover:border-blue-500 transition-colors" />
                  
                  <div className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-6">
                    <div className="min-w-[70px] flex items-center text-slate-400 font-mono text-sm font-medium pt-0.5">
                      <Clock className="h-3 w-3 mr-1.5" />
                      {item.time}
                    </div>
                    
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
                        {item.title}
                      </h4>
                      {item.speaker && (
                        <p className="text-blue-600 font-medium mt-1 text-sm">
                          연사: {item.speaker}
                        </p>
                      )}
                      {item.description && (
                        <p className="text-slate-500 text-sm mt-2">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};