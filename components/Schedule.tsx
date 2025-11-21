import React from 'react';
import { SCHEDULE } from '../constants';
import { MapPin } from 'lucide-react';

export const Schedule: React.FC = () => {
  const day1 = SCHEDULE[0];
  const day2 = SCHEDULE[1];
  const day3 = SCHEDULE[2];

  const renderDayContent = (day: typeof day1, isCombined: boolean) => (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className={`px-5 py-4 border-b-2 border-slate-200 ${isCombined ? 'bg-slate-50/50' : 'bg-slate-100 rounded-t-xl'}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="bg-blue-600 text-white text-xs font-bold px-2.5 py-1 rounded shadow-sm uppercase tracking-wide">
            {day.date.split(' - ')[1] || 'Day'}
          </span>
          <span className="text-sm font-bold text-slate-700">
            {day.date.split(' - ')[0]}
          </span>
        </div>
        <div className="flex items-center text-slate-600 text-xs font-medium">
          <MapPin className="h-3.5 w-3.5 mr-1.5 shrink-0 text-blue-500" />
          <span className="truncate">{day.location}</span>
        </div>
      </div>

      {/* List */}
      <div className={`p-5 overflow-y-auto flex-grow ${isCombined ? 'bg-white' : 'bg-white rounded-b-xl'}`}>
        <ul className="space-y-6 relative">
          {/* Timeline Line */}
          <div className="absolute left-[6px] top-2 bottom-2 w-0.5 bg-slate-200"></div>
          
          {day.items.map((item, idx) => (
            <li key={idx} className="relative pl-6 group">
              {/* Timeline Dot */}
              <div className="absolute left-0 top-1.5 w-[13px] h-[13px] rounded-full bg-white border-[3px] border-slate-300 group-hover:border-blue-500 transition-colors z-10 shadow-sm" />
              
              <div className="flex flex-col">
                <span className="text-xs font-mono text-slate-500 font-bold mb-0.5 leading-none">
                  {item.time}
                </span>
                <h4 className="text-sm font-bold text-slate-900 leading-snug group-hover:text-blue-700 transition-colors">
                  {item.title}
                </h4>
                {item.speaker && (
                  <p className="text-xs text-blue-600 font-bold mt-1">
                    {item.speaker}
                  </p>
                )}
                {item.description && (
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed whitespace-pre-wrap">
                    {item.description}
                  </p>
                )}
                {item.subItems && (
                  <div className="mt-2 space-y-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    {item.subItems.map((sub, subIdx) => (
                      <div key={subIdx}>
                        {sub.title && (
                          <p className="text-xs text-slate-800 leading-snug font-medium">
                            {sub.title}
                          </p>
                        )}
                        {sub.speaker && (
                          <p className="text-xs text-blue-600 font-bold leading-snug pl-0.5 mt-0.5">
                            {sub.speaker}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-stretch">
      {/* Day 1 Column */}
      <div className="lg:w-1/3 flex flex-col">
         <div className="rounded-xl shadow-lg border-2 border-slate-300 flex flex-col h-full bg-white transition-transform hover:-translate-y-1 duration-300">
            {renderDayContent(day1, false)}
         </div>
      </div>

      {/* Vertical Divider (Desktop only) */}
      <div className="hidden lg:flex flex-col items-center justify-center">
         <div className="h-full w-px border-r-2 border-dashed border-slate-300/70 relative">
             {/* Optional: Add a 'VS' or arrow circle if desired, but a simple dashed line is clean as per 'vertical separator' request */}
         </div>
      </div>

      {/* Day 2 & 3 Combined Column */}
      <div className="lg:w-2/3 flex flex-col">
        <div className="rounded-xl shadow-lg border-2 border-slate-300 h-full bg-white flex flex-col lg:flex-row overflow-hidden transition-transform hover:-translate-y-1 duration-300">
            {/* Day 2 */}
            <div className="flex-1 border-b-2 lg:border-b-0 lg:border-r-2 border-slate-200 border-dashed">
                {renderDayContent(day2, true)}
            </div>
            {/* Day 3 */}
            <div className="flex-1">
                 {renderDayContent(day3, true)}
            </div>
        </div>
      </div>
    </div>
  );
};