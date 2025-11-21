import React from 'react';
import { Calendar, MapPin, Users, CreditCard, Clock, ExternalLink } from 'lucide-react';

export const KeyInfo: React.FC = () => {
  return (
    <section id="key-info" className="relative z-20 -mt-16 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-7xl mx-auto bg-white rounded-2xl shadow-xl border border-slate-100 p-6 md:p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 divide-y md:divide-y-0 md:divide-x divide-slate-100">
          
          {/* Date & Location */}
          <div className="pt-4 md:pt-0 px-0 md:px-4 first:pl-0">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                <Calendar className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg">일시 및 장소</h3>
            </div>
            <div className="space-y-3 text-sm text-slate-600">
              <div>
                <span className="font-bold text-slate-900 block mb-1">1일차: 12.20(토)</span>
                <a 
                  href="https://naver.me/F6lTYr1P" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-start gap-1 hover:text-blue-600 transition-colors group"
                >
                  <MapPin className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-slate-400 group-hover:text-blue-500" />
                  <span className="underline decoration-slate-200 underline-offset-2 group-hover:decoration-blue-500">한국컨퍼런스센터 (강남)</span>
                </a>
              </div>
              <div>
                <span className="font-bold text-slate-900 block mb-1">2·3일차: 12.27-28(토·일)</span>
                <a 
                  href="https://naver.me/5eUcdiUA" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-start gap-1 hover:text-blue-600 transition-colors group"
                >
                  <MapPin className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-slate-400 group-hover:text-blue-500" />
                  <span className="underline decoration-slate-200 underline-offset-2 group-hover:decoration-blue-500">가평 교원비전센터</span>
                </a>
              </div>
            </div>
          </div>

          {/* Participants */}
          <div className="pt-8 md:pt-0 px-0 md:px-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                <Users className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg">참가 대상</h3>
            </div>
            <div className="text-sm text-slate-600 space-y-2">
              <p className="font-medium text-slate-800 text-base">
                국내 의과대학 재학생 80명
              </p>
              <p className="text-slate-500">
                (예과 포함, 휴학생 포함)
              </p>
              <div className="inline-block bg-slate-50 px-2 py-1.5 rounded text-xs text-slate-500">
                <span className="font-semibold">선발기준:</span> 자기소개서 및 지원동기<br/>(학교/학년 안배 예정)
              </div>
            </div>
          </div>

          {/* Fee */}
          <div className="pt-8 md:pt-0 px-0 md:px-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                <CreditCard className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg">참가비</h3>
            </div>
            <div className="text-sm text-slate-600">
              <p className="font-bold text-slate-900 text-2xl mb-1">50,000원</p>
              <p className="text-xs leading-relaxed text-slate-500">
                * 참가비 전액은 참가자 이름으로<br/>
                <span className="font-semibold text-blue-600">공익법센터 어필(APIL)</span>에 기부됩니다.
              </p>
            </div>
          </div>

          {/* Application */}
          <div className="pt-8 md:pt-0 px-0 md:px-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                <Clock className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg">신청 기간</h3>
            </div>
             <div className="text-sm text-slate-600">
              <p className="font-bold text-red-600 text-lg mb-1">12월 7일(일) 자정까지</p>
              <p className="text-xs text-slate-500 mb-4">
                합격자 발표: 12월 10일(화) 개별 안내
              </p>
              <p className="text-xs text-slate-500 mb-4 font-medium">
                문의 : 02-2646-0852<br/>instagram DM @doc_lounge
              </p>
              <a 
                href="https://docs.google.com/forms/d/e/1FAIpQLSfxxwS7TZ1mDRLnCgqB4q-hegc7-w1l9IUFK0XVA8DxRm3TCA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center w-full px-4 py-2.5 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 transform hover:-translate-y-0.5"
              >
                지금 지원하기
              </a>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};