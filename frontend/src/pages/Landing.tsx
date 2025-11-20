import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

export const Landing: React.FC = () => {
  const navigate = useNavigate();
  const [question, setQuestion] = useState('');

  const handleAsk = () => {
    if (question.trim()) {
      navigate('/ask', { state: { initialQuestion: question } });
    }
  };

  return (
    <div 
      className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50 flex items-center justify-center px-4 py-12"
      style={{ fontFamily: "'Montserrat', sans-serif" }}
    >
      <div className="max-w-5xl w-full space-y-12">
        {/* Hero Section - Centered */}
        <div className="text-center space-y-8">
          <h1 className="text-5xl lg:text-7xl font-bold text-secondary-900 leading-tight" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            AI Governance Literacy Platform
          </h1>
          <p className="text-xl lg:text-2xl text-secondary-600 max-w-3xl mx-auto leading-relaxed px-4">
            Making AI regulation and risk frameworks understandable, trustworthy, and accessible 
            to policy professionals, researchers, civil society, and the public.
          </p>
        </div>

        {/* Search Card - Enhanced Design */}
        <div className="bg-white rounded-2xl shadow-xl p-10 transform transition-all duration-300 hover:shadow-2xl border border-secondary-100">
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-semibold text-secondary-900 mb-4" style={{ fontFamily: "'Montserrat', sans-serif" }}>
                Ask about AI regulation
              </h2>
              <p className="text-lg text-secondary-600 leading-relaxed">
                Get answers about AI governance frameworks, regulations, and best practices from 
                trusted sources.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <Input
                placeholder="e.g., What are the key requirements of the EU AI Act?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
                className="flex-1 text-lg py-4 px-6 rounded-xl border-2 border-secondary-200 focus:border-primary-500 transition-colors"
              />
              <Button 
                onClick={handleAsk} 
                size="lg"
                className="px-8 py-4 text-lg font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
              >
                Ask
              </Button>
            </div>
          </div>
        </div>

        {/* Features Grid - Enhanced Spacing */}
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 border border-secondary-100">
            <div className="mb-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 mb-3" style={{ fontFamily: "'Montserrat', sans-serif" }}>
                Trusted Sources
              </h3>
              <p className="text-secondary-600 leading-relaxed">
                Answers are grounded in official regulatory documents and established frameworks.
              </p>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 border border-secondary-100">
            <div className="mb-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 mb-3" style={{ fontFamily: "'Montserrat', sans-serif" }}>
                Clear Explanations
              </h3>
              <p className="text-secondary-600 leading-relaxed">
                Complex regulations made accessible with clear, cited explanations.
              </p>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 border border-secondary-100">
            <div className="mb-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 mb-3" style={{ fontFamily: "'Montserrat', sans-serif" }}>
                Always Learning
              </h3>
              <p className="text-secondary-600 leading-relaxed">
                Our knowledge base continuously expands with new regulations and frameworks.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
