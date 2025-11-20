import React from 'react';

interface SectionProps {
  id?: string;
  className?: string;
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  dark?: boolean;
}

export const Section: React.FC<SectionProps> = ({ 
  id, 
  className = '', 
  children, 
  title, 
  subtitle,
  dark = false 
}) => {
  return (
    <section 
      id={id} 
      className={`py-16 md:py-24 px-4 sm:px-6 lg:px-8 ${dark ? 'bg-slate-900 text-white' : 'bg-white text-slate-900'} ${className}`}
    >
      <div className="max-w-7xl mx-auto">
        {(title || subtitle) && (
          <div className="mb-12 text-center">
            {title && (
              <h2 className={`text-3xl md:text-4xl font-bold mb-4 ${dark ? 'text-white' : 'text-slate-900'}`}>
                {title}
              </h2>
            )}
            {subtitle && (
              <p className={`text-lg md:text-xl max-w-2xl mx-auto ${dark ? 'text-slate-300' : 'text-slate-600'}`}>
                {subtitle}
              </p>
            )}
            <div className={`mt-6 h-1 w-20 mx-auto rounded-full ${dark ? 'bg-blue-500' : 'bg-blue-600'}`} />
          </div>
        )}
        {children}
      </div>
    </section>
  );
};