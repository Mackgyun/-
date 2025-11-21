import React from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { KeyInfo } from './components/KeyInfo';
import { Section } from './components/Section';
import { Schedule } from './components/Schedule';
import { Speakers } from './components/Speakers';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-white selection:bg-blue-100 selection:text-blue-900">
      <Navbar />
      
      <Hero />
      
      <KeyInfo />

      <Section id="about" className="bg-white pt-24 pb-24">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              새로운 시대를 여는 <span className="text-blue-600">의대생들의 만남</span>
            </h2>
            <div className="h-1 w-20 bg-blue-600 mx-auto rounded-full"/>
          </div>

          {/* Intro Text */}
          <div className="text-lg text-slate-700 leading-relaxed space-y-6 text-justify break-keep mb-12 px-4">
            <p>
              2001년부터 10회에 걸쳐 진행된 ‘MSD청년슈바이처캠프’와 2007년부터 8회에 걸쳐 진행된 ‘메디슨 청년의사 자원봉사 체험캠프’에 이어, 오랜만에 청년의사가 ‘의대생 캠프’를 진행합니다.
            </p>
            <p>
              이번 캠프의 주제는 ‘국제보건’과 ‘미래의료’입니다. 학교에서는 쉽게 만날 수 없는 최고의 전문가들을 만나고, 비슷한 열정을 지닌 동료들과 유대를 쌓는 ‘제1회 KMI 청년의사 글로벌 헬스 리더십 캠프’에 의대생들의 많은 지원 바랍니다. 이 캠프는 연 2회 2박3일간 진행되며, 1회 캠프는 예외적으로 1박3일 일정으로 진행됩니다.
            </p>
          </div>

          {/* Image Section */}
          <div className="mb-12 px-4 md:px-0">
            <div className="relative aspect-[21/9] w-full overflow-hidden rounded-2xl shadow-lg group">
              <img 
                src="https://images.unsplash.com/photo-1576091160550-2187d80018fd?auto=format&fit=crop&q=80&w=2070" 
                alt="Medical students seminar and discussion" 
                className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-blue-900/20 to-transparent"/>
            </div>
          </div>

          {/* Purpose Box (Highlighted) */}
          <div className="bg-slate-50 rounded-3xl p-8 md:p-12 shadow-sm border border-slate-100 mb-12 mx-2 md:mx-0">
            <h3 className="text-2xl font-bold text-slate-900 mb-8 flex items-center border-b pb-4 border-slate-200">
              <span className="bg-blue-600 w-1.5 h-8 mr-3 rounded-full"></span>
              취지
            </h3>
            <div className="text-lg text-slate-700 space-y-6 leading-relaxed text-justify break-keep">
              <p>
                21세기의 의료는 국경을 넘나드는 협력과 연대 없이는 완성될 수 없습니다. 감염병, 기후변화, 보건의료 접근성 불평등, 난민 문제 등 보건의료 및 공중보건과 밀접한 관련이 있는 전 지구적인 위기들은 단일 국가의 대응으로는 극복하기 어렵습니다.
              </p>
              <p>
                이러한 상황에서 국제기구, NGO, 정부 주도 ODA 프로젝트 등 다양한 무대에서 의사들의 역할은 점점 더 중요해지고 있습니다. 한국에서도 최근 국제보건에 대한 의대생과 젊은 의사들의 관심이 눈에 띄게 증가하고 있습니다. 하지만 여전히 이 분야에 대한 정보는 부족하고, 실제 활동하고 있는 전문가들과의 접점은 매우 제한적입니다.
              </p>
              <p>
                또한, 인공지능의 등장으로 대표되는 기술 혁신과 고령화로 대표되는 의료환경 변화 속에서, 미래의 의료는 지금과 크게 달라질 것으로 예측되지만 그에 대해 적극적으로 대비하는 움직임은 찾아보기 어렵습니다.
              </p>
            </div>
          </div>

          {/* Conclusion */}
          <div className="text-center px-4">
            <p className="text-xl md:text-2xl font-semibold text-slate-900 leading-relaxed break-keep">
              이에 따라, 신문 청년의사와 KMI한국의학연구소는 <br className="hidden md:block"/>
              국제보건 및 미래의료에 관심 있는 의대생들이 실제 현장의 이야기를 듣고, <br className="hidden md:block"/>
              진로를 모색하며, 서로의 열정을 공유할 수 있는 장을 마련합니다.
            </p>
          </div>
        </div>
      </Section>

      <Section id="schedule" title="프로그램 일정" subtitle="1박 3일간 펼쳐지는 지식과 영감의 여정" className="bg-gradient-to-b from-slate-50 via-blue-50/30 to-slate-100">
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
              <p className="text-sm font-medium text-slate-400">문의 : 02-2646-0852, instagram DM @doc_lounge</p>
              <p className="text-sm mt-2">Copyright © The Korean Doctors Weekly. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;