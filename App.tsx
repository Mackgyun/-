import React from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { KeyInfo } from './components/KeyInfo';
import { Section } from './components/Section';
import { Schedule } from './components/Schedule';
import { Speakers } from './components/Speakers';
import { CheckCircle2, HeartHandshake, Lightbulb, Users } from 'lucide-react';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-white selection:bg-blue-100 selection:text-blue-900">
      <Navbar />
      
      <Hero />
      
      <KeyInfo />

      <Section id="about" className="bg-white pt-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-6">
              왜 <span className="text-blue-600">청년의사 리더십 캠프</span>인가요?
            </h2>
            <p className="text-lg text-slate-600 mb-6 leading-relaxed">
              2001년부터 10회에 걸쳐 진행된 'MSD청년슈바이처캠프'와 2007년부터 이어진 '메디슨 청년의사 자원봉사 체험캠프'의 정신을 잇습니다.
            </p>
            <p className="text-lg text-slate-600 mb-8 leading-relaxed">
              21세기의 의료는 국경을 넘나드는 협력 없이는 완성될 수 없습니다. 이번 캠프는 
              <span className="font-bold text-slate-900"> '국제보건'</span>과 
              <span className="font-bold text-slate-900"> '미래의료'</span>를 주제로,
              강의실에서는 만날 수 없는 최고의 전문가들과 함께 깊이 있는 통찰을 나눕니다.
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: Users, text: "동료들과의 유대" },
                { icon: Lightbulb, text: "미래의료 통찰" },
                { icon: HeartHandshake, text: "국제보건 멘토링" },
                { icon: CheckCircle2, text: "진로 모색" }
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 bg-slate-50 p-3 rounded-lg">
                  <item.icon className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-slate-700">{item.text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="relative">
            <div className="aspect-video rounded-2xl overflow-hidden shadow-2xl transform md:rotate-2 hover:rotate-0 transition-transform duration-500">
               <img 
                src="https://picsum.photos/800/600?grayscale" 
                alt="Medical Students Discussion" 
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-tr from-blue-900/50 to-transparent" />
              <div className="absolute bottom-6 left-6 text-white">
                <p className="font-bold text-lg">주최: 신문 청년의사</p>
                <p className="text-sm opacity-90">후원: 보건복지부 · KMI 한국의학연구소</p>
              </div>
            </div>
          </div>
        </div>
      </Section>

      <Section id="schedule" title="프로그램 일정" subtitle="1박 3일간 펼쳐지는 지식과 영감의 여정" className="bg-slate-50">
        <Schedule />
      </Section>

      <Section id="speakers" title="함께하는 전문가들" subtitle="각 분야 최고의 전문가들이 여러분의 멘토가 됩니다">
        <Speakers />
      </Section>

      <Section id="apply" className="bg-slate-900" dark>
        <div className="text-center py-12">
          <div className="inline-flex flex-col items-center bg-white/5 border border-white/10 rounded-3xl p-8 md:p-16 max-w-4xl mx-auto w-full">
            <span className="px-4 py-1 rounded-full bg-blue-500/20 text-blue-300 font-semibold text-sm mb-6">
              모집 마감 임박
            </span>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 leading-tight">
              미래 의료의 주역이 될<br/>
              여러분의 도전을 기다립니다
            </h2>
            <p className="text-slate-400 mb-10 text-xl max-w-2xl">
              12월 7일(일) 자정까지 접수 가능합니다.<br/>
              지금 바로 지원하세요.
            </p>
            <a 
              href="https://docs.google.com/forms/d/e/1FAIpQLSfxxwS7TZ1mDRLnCgqB4q-hegc7-w1l9IUFK0XVA8DxRm3TCA/viewform" 
              target="_blank"
              rel="noopener noreferrer"
              className="px-12 py-5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xl font-bold rounded-full transition-all shadow-xl shadow-blue-600/30 hover:shadow-blue-600/50 hover:-translate-y-1 w-full md:w-auto"
            >
              지원 신청하기
            </a>
            <p className="mt-6 text-sm text-slate-500">
              * 합격자 발표: 12월 10일(화) 개별 안내
            </p>
          </div>
        </div>
      </Section>

      <footer className="bg-slate-950 text-slate-500 py-12 border-t border-slate-900">
        <div className="max-w-7xl mx-auto px-4 text-center md:text-left">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h5 className="text-white font-bold text-lg mb-4">KMI 청년의사 글로벌 헬스 리더십 캠프</h5>
              <p className="mb-2">주최: 신문 청년의사</p>
              <p>후원: 보건복지부, KMI 한국의학연구소</p>
            </div>
            <div className="md:text-right">
              <p className="text-sm">문의: 청년의사 편집국</p>
              <p className="text-sm mt-2">Copyright © The Korean Doctors Weekly. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;