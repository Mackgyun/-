import React from 'react';

export const Hero: React.FC = () => {
  return (
    <div className="relative bg-slate-900 min-h-[600px] lg:h-[80vh] flex items-center justify-center overflow-hidden pb-20">
      {/* Background Image Overlay */}
      <div className="absolute inset-0 z-0">
        <img 
          src="https://picsum.photos/1920/1080?grayscale&blur=2" 
          alt="Background" 
          className="w-full h-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-blue-900/70 to-slate-900/90" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-block mb-6 px-4 py-1.5 rounded-full bg-blue-500/20 border border-blue-400/30 backdrop-blur-sm">
          <span className="text-blue-200 font-semibold tracking-wider text-sm uppercase">1st KMI Youth Doctor Camp</span>
        </div>
        
        <h1 className="text-4xl sm:text-5xl md:text-7xl font-black text-white tracking-tight mb-6 leading-tight">
          글로벌 헬스 <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-teal-300">리더십 캠프</span>
        </h1>
        
        <p className="mt-4 text-xl md:text-2xl text-slate-300 max-w-3xl mx-auto font-light leading-relaxed">
          국제보건과 미래의료에 관심 있는 의대생을 위한 특별한 여정.<br className="hidden md:block" />
          최고의 전문가들과 함께 당신의 비전을 넓히세요.
        </p>

        <div className="mt-10">
          <a 
            href="#key-info"
            className="inline-block px-8 py-4 bg-white/10 backdrop-blur-md border border-white/20 text-white font-bold text-lg rounded-full hover:bg-white/20 transition-all duration-300"
          >
            캠프 세부 정보 확인하기
          </a>
        </div>
      </div>
      
      {/* Scroll Indicator */}
      <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 animate-bounce text-slate-400 hidden lg:block">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </div>
  );
};