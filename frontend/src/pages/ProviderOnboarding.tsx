import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  MapPin, Upload, CheckCircle, DollarSign, Bot, 
  Shield, Camera, Briefcase, Star, Map as MapIcon,
  ChevronRight, ChevronLeft, Loader2, User, Phone, 
  Calendar, FileText, Award, Mail, Lock, Eye, EyeOff,
  Volume2, Trash2, Image as ImageIcon
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, useMapEvents, Polygon, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import toast from 'react-hot-toast';
import { authAPI, aptitudeAPI } from '../services/api';

// Fix Leaflet icon issue
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

// Aptitude Test Data for Professions
const APTITUDE_TEST_DATA: any = {
  plumbing: [
    { id: 1, question: "aptitude.plumbing.q1.text", options: ["aptitude.plumbing.q1.o1", "aptitude.plumbing.q1.o2", "aptitude.plumbing.q1.o3", "aptitude.plumbing.q1.o4"], answer: 1 },
    { id: 2, question: "aptitude.plumbing.q2.text", options: ["aptitude.plumbing.q2.o1", "aptitude.plumbing.q2.o2", "aptitude.plumbing.q2.o3", "aptitude.plumbing.q2.o4"], answer: 2 },
    { id: 3, question: "aptitude.plumbing.q3.text", options: ["aptitude.plumbing.q3.o1", "aptitude.plumbing.q3.o2", "aptitude.plumbing.q3.o3", "aptitude.plumbing.q3.o4"], answer: 1 },
    { id: 4, question: "aptitude.plumbing.q4.text", options: ["aptitude.plumbing.q4.o1", "aptitude.plumbing.q4.o2", "aptitude.plumbing.q4.o3", "aptitude.plumbing.q4.o4"], answer: 1 },
    { id: 5, question: "aptitude.plumbing.q5.text", options: ["aptitude.plumbing.q5.o1", "aptitude.plumbing.q5.o2", "aptitude.plumbing.q5.o3", "aptitude.plumbing.q5.o4"], answer: 1 }
  ],
  electrical: [
    { id: 1, question: "aptitude.electrical.q1.text", options: ["aptitude.electrical.q1.o1", "aptitude.electrical.q1.o2", "aptitude.electrical.q1.o3", "aptitude.electrical.q1.o4"], answer: 3 },
    { id: 2, question: "aptitude.electrical.q2.text", options: ["aptitude.electrical.q2.o1", "aptitude.electrical.q2.o2", "aptitude.electrical.q2.o3", "aptitude.electrical.q2.o4"], answer: 1 },
    { id: 3, question: "aptitude.electrical.q3.text", options: ["aptitude.electrical.q3.o1", "aptitude.electrical.q3.o2", "aptitude.electrical.q3.o3", "aptitude.electrical.q3.o4"], answer: 2 },
    { id: 4, question: "aptitude.electrical.q4.text", options: ["aptitude.electrical.q4.o1", "aptitude.electrical.q4.o2", "aptitude.electrical.q4.o3", "aptitude.electrical.q4.o4"], answer: 3 },
    { id: 5, question: "aptitude.electrical.q5.text", options: ["aptitude.electrical.q5.o1", "aptitude.electrical.q5.o2", "aptitude.electrical.q5.o3", "aptitude.electrical.q5.o4"], answer: 1 }
  ],
  painter: [
    { id: 1, question: "aptitude.painter.q1.text", options: ["aptitude.painter.q1.o1", "aptitude.painter.q1.o2", "aptitude.painter.q1.o3", "aptitude.painter.q1.o4"], answer: 1 },
    { id: 2, question: "aptitude.painter.q2.text", options: ["aptitude.painter.q2.o1", "aptitude.painter.q2.o2", "aptitude.painter.q2.o3", "aptitude.painter.q2.o4"], answer: 1 },
    { id: 3, question: "aptitude.painter.q3.text", options: ["aptitude.painter.q3.o1", "aptitude.painter.q3.o2", "aptitude.painter.q3.o3", "aptitude.painter.q3.o4"], answer: 1 },
    { id: 4, question: "aptitude.painter.q4.text", options: ["aptitude.painter.q4.o1", "aptitude.painter.q4.o2", "aptitude.painter.q4.o3", "aptitude.painter.q4.o4"], answer: 2 },
    { id: 5, question: "aptitude.painter.q5.text", options: ["aptitude.painter.q5.o1", "aptitude.painter.q5.o2", "aptitude.painter.q5.o3", "aptitude.painter.q5.o4"], answer: 1 }
  ],
  cleaning: [
    { id: 1, question: "aptitude.cleaning.q1.text", options: ["aptitude.cleaning.q1.o1", "aptitude.cleaning.q1.o2", "aptitude.cleaning.q1.o3", "aptitude.cleaning.q1.o4"], answer: 1 },
    { id: 2, question: "aptitude.cleaning.q2.text", options: ["aptitude.cleaning.q2.o1", "aptitude.cleaning.q2.o2", "aptitude.cleaning.q2.o3", "aptitude.cleaning.q2.o4"], answer: 1 },
    { id: 3, question: "aptitude.cleaning.q3.text", options: ["aptitude.cleaning.q3.o1", "aptitude.cleaning.q3.o2", "aptitude.cleaning.q3.o3", "aptitude.cleaning.q3.o4"], answer: 1 },
    { id: 4, question: "aptitude.cleaning.q4.text", options: ["aptitude.cleaning.q4.o1", "aptitude.cleaning.q4.o2", "aptitude.cleaning.q4.o3", "aptitude.cleaning.q4.o4"], answer: 1 },
    { id: 5, question: "aptitude.cleaning.q5.text", options: ["aptitude.cleaning.q5.o1", "aptitude.cleaning.q5.o2", "aptitude.cleaning.q5.o3", "aptitude.cleaning.q5.o4"], answer: 2 }
  ],
  beauty: [
    { id: 1, question: "Before applying makeup, it is essential to...", options: ["Skip moisturizer", "Cleanse and prep the skin", "Apply powder first", "Use cold water"], answer: 1 },
    { id: 2, question: "What is the correct way to sanitize makeup brushes?", options: ["Rinse with hot water", "Use a dedicated brush cleanser", "Use dish soap only", "Wipe them with a towel"], answer: 1 },
    { id: 3, question: "Which ingredient is a common allergen in skincare?", options: ["Hyaluronic acid", "Fragrance/Parfum", "Aloe vera", "Glycerin"], answer: 1 },
    { id: 4, question: "When styling hair with heat, you should always...", options: ["Apply heat protectant spray", "Style it while dripping wet", "Turn iron to max heat", "Skip conditioner"], answer: 0 },
    { id: 5, question: "A patch test is used to...", options: ["Check skin tone", "Test for allergic reactions", "Estimate product duration", "Hydrate the skin"], answer: 1 }
  ],
  fitness: [
    { id: 1, question: "Which of these is a compound exercise?", options: ["Bicep curl", "Leg extension", "Squat", "Calf raise"], answer: 2 },
    { id: 2, question: "What is the primary muscle targeted during a standard push-up?", options: ["Latissimus dorsi", "Pectoralis major", "Hamstrings", "Glutes"], answer: 1 },
    { id: 3, question: "How do you treat a minor muscle sprain immediately after injury?", options: ["RICE (Rest, Ice, Compression, Elevation)", "Apply heat immediately", "Stretch it vigorously", "Ignore it"], answer: 0 },
    { id: 4, question: "What is an appropriate rest time between high-intensity sets?", options: ["10 seconds", "1-3 minutes", "10 minutes", "No rest"], answer: 1 },
    { id: 5, question: "A dynamic warmup should consist of...", options: ["Holding stretches for 60s", "Active movements matching the workout", "Sleeping", "Lifting max weight immediately"], answer: 1 }
  ],
  delivery: [
    { id: 1, question: "What is the most important rule when handling fragile packages?", options: ["Stack them at the bottom", "Secure them and drive smoothly", "Throw them to save time", "Leave them upside down"], answer: 1 },
    { id: 2, question: "If a customer is not home to sign for a high-value package...", options: ["Leave it at the door", "Ask a random neighbor to sign", "Follow standard redelivery procedure", "Keep it for yourself"], answer: 2 },
    { id: 3, question: "How should you lift heavy boxes to prevent back injury?", options: ["Bend your back, keep legs straight", "Bend at the knees and keep your back straight", "Lift rapidly", "Hold it far away from your body"], answer: 1 },
    { id: 4, question: "When navigating a new route, the best practice is...", options: ["Speed to save time", "Use GPS and pre-plan stops", "Guess the way", "Ask pedestrians at every turn"], answer: 1 },
    { id: 5, question: "Upon delivering food items, ensuring hygiene means...", options: ["Opening the bag to check", "Using insulated, clean thermal bags", "Placing it on the bare ground", "Eating the fries"], answer: 1 }
  ],
  repair: [
    { id: 1, question: "When diagnosing a broken appliance, what is the first step?", options: ["Replace the motor", "Check the power supply/cord", "Take the entire thing apart", "Hit it with a hammer"], answer: 1 },
    { id: 2, question: "What does HVAC stand for?", options: ["Heating, Ventilation, and Air Conditioning", "High Voltage Alternating Current", "Home Vacuum And Cleaning", "Heat Valve And Control"], answer: 0 },
    { id: 3, question: "WD-40 is primarily used as a...", options: ["Permanent glue", "Water displacer and light lubricant", "Electrical insulator", "Paint thinner"], answer: 1 },
    { id: 4, question: "To loosen a rusted bolt safely, you should...", options: ["Apply penetrating oil and wait", "Use extreme force immediately", "Cut it off instantly", "Heat it until it melts"], answer: 0 },
    { id: 5, question: "What safety gear is essential when using a grinder?", options: ["Earplugs only", "Safety glasses and gloves", "A hat", "None"], answer: 1 }
  ],
  tutoring: [
    { id: 1, question: "If a student repeatedly struggles with a concept, the best approach is to...", options: ["Tell them to study harder", "Explain it exactly the same way louder", "Try a different teaching method", "Skip the topic entirely"], answer: 2 },
    { id: 2, question: "What is the primary purpose of formative assessment?", options: ["Assigning a final grade", "Tracking ongoing student progress", "Punishing the student", "Fulfilling legal requirements"], answer: 1 },
    { id: 3, question: "Active learning involves...", options: ["The student listening silently for hours", "Engaging the student in problem-solving", "The tutor doing all the talking", "Reading from a textbook only"], answer: 1 },
    { id: 4, question: "When setting goals for a tutoring session, they should be...", options: ["Vague and general", "SMART (Specific, Measurable, Achievable, Relevant, Time-bound)", "Impossible to achieve", "Decided entirely by the parent"], answer: 1 },
    { id: 5, question: "How should you handle a situation where you don't know the answer?", options: ["Make something up", "Ignore the question", "Admit you don't know and look it up together", "Tell them it won't be on the test"], answer: 2 }
  ]
};

const ProviderOnboarding: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [profilePhotoPreview, setProfilePhotoPreview] = useState<string | null>(null);
  
  // Aptitude State
  const [testActive, setTestActive] = useState(false);
  const [backendQuestions, setBackendQuestions] = useState<any[]>([]);
  const [isLoadingBackendQuestions, setIsLoadingBackendQuestions] = useState(false);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [testAnswers, setTestAnswers] = useState<number[]>([]);
  const [testScore, setTestScore] = useState<number | null>(null);
  
  // Timer State
  const [timeLeft, setTimeLeft] = useState<number>(360); // 6 mins
  const [timerActive, setTimerActive] = useState<boolean>(false);

  const [formData, setFormData] = useState({
    // Personal Details (Step 1)
    fullName: '',
    email: '',
    password: '',
    age: '',
    phone: '',
    gender: '' as '' | 'male' | 'female' | 'other' | 'prefer_not_to_say',
    bio: '',
    experienceYears: '',
    profilePhoto: null as File | null,
    workGallery: [] as { preview: string; file: File; type: string; id: string }[],
    portfolio: [] as { file: File; caption: string; preview: string }[],
    // Business & Location
    businessName: '',
    location: { lat: 12.9716, lng: 77.5946 } as { lat: number; lng: number },
    serviceAreaType: 'radius' as 'radius' | 'polygon',
    radius: 5,
    polygonPoints: [] as [number, number][],
    categories: [] as string[],
    suggestedCategories: [] as string[],
    documents: {
      idFront: null as File | null,
      idBack: null as File | null,
      selfie: null as File | null,
      idType: 'aadhar' as 'aadhar' | 'pan',
      idNumber: '',
      isIdVerified: false,
    },
    aptitudeScore: 0,
    hourlyRate: '',
    emergencyRate: '',
    aiBotEnabled: false,
    aiAggression: 'balanced' as 'conservative' | 'balanced' | 'aggressive',
  });

  useEffect(() => {
    let interval: any;
    if (timerActive && timeLeft > 0) {
      interval = setInterval(() => setTimeLeft(prev => prev - 1), 1000);
    } else if (timerActive && timeLeft === 0 && testActive) {
      // Auto-submit when time is up
      let correct = 0;
      const questions = backendQuestions.length > 0 ? backendQuestions : (APTITUDE_TEST_DATA[formData.categories[0] || 'painter'] || APTITUDE_TEST_DATA['painter']);
      questions.forEach((q: any, i: number) => {
        if (testAnswers[i] === q.answer) correct++;
      });
      const finalScore = Math.round((correct / questions.length) * 100);
      setTestScore(finalScore);
      setTestActive(false);
      setTimerActive(false);
      toast.error('Time is up!');
    }
    return () => clearInterval(interval);
  }, [timerActive, timeLeft, testActive, testAnswers, backendQuestions, formData.categories]);

  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);

  const allCategories = [
    { value: 'plumbing', label: 'Plumbing', icon: '🔧' },
    { value: 'electrical', label: 'Electrical', icon: '⚡' },
    { value: 'cleaning', label: 'Cleaning', icon: '🧹' },
    { value: 'painter', label: 'Painting', icon: '🎨' },
    { value: 'beauty', label: 'Beauty', icon: '💄' },
    { value: 'fitness', label: 'Fitness', icon: '💪' },
    { value: 'delivery', label: 'Delivery', icon: '📦' },
    { value: 'repair', label: 'Repair', icon: '🔨' },
    { value: 'tutoring', label: 'Tutoring', icon: '📚' },
  ];

  const steps = [
    { number: 1, title: 'Personal Info', icon: User, description: 'Your basic details' },
    { number: 2, title: 'Base Location', icon: MapPin, description: 'Select your home base' },
    { number: 3, title: 'Service Area', icon: MapIcon, description: 'Define where you work' },
    { number: 4, title: 'Categories', icon: CheckCircle, description: 'AI suggested skills' },
    { number: 5, title: 'Verification', icon: Shield, description: 'Identity & Liveness' },
    { number: 6, title: 'Background', icon: Shield, description: 'Trust & Safety' },
    { number: 7, title: 'Aptitude Test', icon: FileText, description: 'Skill Assessment' },
    { number: 8, title: 'Pricing & AI', icon: Bot, description: 'Rates & Bot settings' },
  ];

  const LocationMarker = () => {
    useMapEvents({
      click(e) {
        setFormData(prev => ({ ...prev, location: e.latlng }));
      },
    });
    return <Marker position={formData.location} />;
  };

  const PolygonSelector = () => {
    useMapEvents({
      click(e) {
        if (formData.serviceAreaType === 'polygon') {
          setFormData(prev => ({
            ...prev,
            polygonPoints: [...prev.polygonPoints, [e.latlng.lat, e.latlng.lng]]
          }));
        }
      },
    });
    return formData.polygonPoints.length > 0 ? (
      <Polygon positions={formData.polygonPoints} color="purple" />
    ) : null;
  };

  const fetchAiSuggestions = async () => {
    setIsAiLoading(true);
    // Mock AI suggestion based on location demand
    setTimeout(() => {
      setFormData(prev => ({
        ...prev,
        suggestedCategories: ['plumbing', 'electrical', 'repair']
      }));
      setIsAiLoading(false);
      toast.success('AI suggestions generated based on local demand!');
    }, 1500);
  };

  useEffect(() => {
    if (currentStep === 4 && formData.suggestedCategories.length === 0) {
      fetchAiSuggestions();
    }
  }, [currentStep]);

  const handleProfilePhotoUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setProfilePhotoPreview(e.target?.result as string);
      setFormData(prev => ({ ...prev, profilePhoto: file }));
    };
    reader.readAsDataURL(file);
  };

  const speakText = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    if (i18n.language === 'hi') utterance.lang = 'hi-IN';
    else if (i18n.language === 'mr') utterance.lang = 'mr-IN';
    else utterance.lang = 'en-US';
    
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  // Fetch questions when test starts
  const startAssessment = async () => {
    const category = formData.categories[0] || 'painter';
    setIsLoadingBackendQuestions(true);
    try {
      const data = await aptitudeAPI.getQuestions(category);
      setBackendQuestions(data.questions);
      setTestActive(true);
      setCurrentQuestionIdx(0);
      setTestAnswers([]);
      setTestScore(null);
      setTimeLeft(360);
      setTimerActive(true);
    } catch (error) {
      console.error('Failed to fetch aptitude questions:', error);
      toast.error('Failed to load assessment. Using offline mode.');
      // Fallback to local data
      setBackendQuestions(APTITUDE_TEST_DATA[category] || APTITUDE_TEST_DATA['painter']);
      setTestActive(true);
      setCurrentQuestionIdx(0);
      setTestAnswers([]);
      setTestScore(null);
      setTimeLeft(360);
      setTimerActive(true);
    } finally {
      setIsLoadingBackendQuestions(false);
    }
  };

  const handleNext = () => {
    if (currentStep === 1) {
      if (!profilePhotoPreview) {
        toast.error('Please upload a profile photo');
        return;
      }
      if (!formData.fullName.trim()) {
        toast.error('Please enter your full name');
        return;
      }
      if (!formData.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
        toast.error('Please enter a valid email address');
        return;
      }
      if (!formData.password || formData.password.length < 6) {
        toast.error('Password must be at least 6 characters');
        return;
      }
      const ageNum = parseInt(formData.age);
      if (isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
        toast.error('You must be between 18 and 100 years old');
        return;
      }
      const digitsOnly = formData.phone.replace(/\D/g, '');
      if (digitsOnly.length < 10) {
        toast.error('Phone number must contain at least 10 digits');
        return;
      }
    }

    if (currentStep === 5) {
      if (!formData.documents.isIdVerified) {
        toast.error(`Please verify your ${formData.documents.idType.toUpperCase()} before proceeding.`);
        return;
      }
      if (!formData.documents.idFront || !formData.documents.idBack) {
        toast.error('Please upload both Front and Back of your Government ID.');
        return;
      }
      if (!formData.documents.selfie) {
        toast.error('Please capture your Liveness Selfie.');
        return;
      }
    }

    if (currentStep === 7) {
        if (formData.categories.length > 0 && !testActive && testAnswers.length === 0) {
            toast.error("Please complete the aptitude test to prove your skills.");
            return;
        }
    }

    setCurrentStep(prev => Math.min(steps.length, prev + 1));
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(1, prev - 1));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Register the provider account
      const res = await authAPI.register({
        full_name: formData.fullName,
        email: formData.email,
        password: formData.password,
        phone: formData.phone,
        role: 'provider',
        age: parseInt(formData.age),
        gender: formData.gender,
        business_name: formData.businessName,
        bio: formData.bio,
        experience_years: parseInt(formData.experienceYears) || 0,
        base_location: formData.location,
        service_categories: formData.categories,
        aptitude_score: testScore,
        hourly_rate: parseFloat(formData.hourlyRate) || 0,
        emergency_rate: parseFloat(formData.emergencyRate) || 0,
      });

      const data = res; // authAPI already returns res.data


      // Persist token so the user is immediately logged in
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }

      toast.success(`Welcome, ${formData.fullName}! Your Qualification Score is ${testScore}/100 🎉`);
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Registration error:', err);
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'string' ? detail : (Array.isArray(detail) ? detail[0]?.msg : 'Registration failed. Please try again.');
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileUpload = (type: 'idFront' | 'idBack', file: File) => {
    setFormData(prev => ({
      ...prev,
      documents: { ...prev.documents, [type]: file }
    }));
    toast.success(`${type === 'idFront' ? 'Front' : 'Back'} ID uploaded!`);
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      setCameraStream(stream);
      setShowCamera(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      toast.success('Camera started!');
    } catch (error) {
      toast.error('Camera access denied');
    }
  };

  const captureSelfie = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d')?.drawImage(video, 0, 0);
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], 'selfie.jpg', { type: 'image/jpeg' });
          setFormData(prev => ({ ...prev, documents: { ...prev.documents, selfie: file } }));
          stopCamera();
          toast.success('Selfie captured!');
        }
      });
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
      setShowCamera(false);
    }
  };

  const handleGalleryUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setFormData(prev => ({
        ...prev,
        workGallery: [...prev.workGallery, { 
            preview: e.target?.result as string, 
            file, 
            type: file.type,
            id: Math.random().toString(36).substr(2, 9) 
        }]
      }));
      toast.success('Work photo added to gallery!');
    };
    reader.readAsDataURL(file);
  };

  const handlePortfolioUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setFormData(prev => ({
        ...prev,
        portfolio: [...prev.portfolio, { file, caption: '', preview: e.target?.result as string }]
      }));
      toast.success('Portfolio image added!');
    };
    reader.readAsDataURL(file);
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-xl font-bold">{t('Step 1: Personal Information')}</h3>
              <p className="text-gray-500 text-sm mt-1">{t('Tell us about yourself so customers can trust and connect with you.')}</p>
            </div>

            {/* Profile Photo */}
            <div className="flex flex-col items-center gap-4">
              <div className="relative group">
                <div className="w-28 h-28 rounded-full overflow-hidden border-4 border-primary-100 shadow-lg bg-gray-100 flex items-center justify-center">
                  {profilePhotoPreview ? (
                    <img src={profilePhotoPreview} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <User size={48} className="text-gray-300" />
                  )}
                </div>
                <label
                  htmlFor="profilePhoto"
                  className="absolute bottom-0 right-0 bg-primary-500 text-white rounded-full p-2 cursor-pointer shadow-md hover:bg-primary-600 transition-colors group-hover:scale-110"
                >
                  <Camera size={16} />
                </label>
                <input
                  id="profilePhoto"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleProfilePhotoUpload(e.target.files[0])}
                />
              </div>
              <p className="text-xs text-gray-400">{t('Upload a professional profile photo')}</p>
            </div>

            {/* Name & Age Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <User size={14} className="text-primary-500" /> {t('Full Name')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Rahul Sharma"
                  value={formData.fullName}
                  onChange={(e) => setFormData(prev => ({ ...prev, fullName: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Calendar size={14} className="text-primary-500" /> {t('Age')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  placeholder="e.g. 28"
                  min="18"
                  max="80"
                  value={formData.age}
                  onChange={(e) => setFormData(prev => ({ ...prev, age: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
            </div>

            {/* Email & Password Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Mail size={14} className="text-primary-500" /> {t('Email Address')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  placeholder="e.g. rahul@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Lock size={14} className="text-primary-500" /> {t('Password')} <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min 6 characters"
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Phone & Gender Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Phone size={14} className="text-primary-500" /> {t('Phone Number')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="tel"
                  placeholder="e.g. +91 98765 43210"
                  value={formData.phone}
                  onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <User size={14} className="text-primary-500" /> {t('Gender')}
                </label>
                <select
                  value={formData.gender}
                  onChange={(e) => setFormData(prev => ({ ...prev, gender: e.target.value as any }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors bg-white"
                >
                  <option value="">{t('Select gender')}</option>
                  <option value="male">{t('Male')}</option>
                  <option value="female">{t('Female')}</option>
                  <option value="other">{t('Other')}</option>
                  <option value="prefer_not_to_say">{t('Prefer not to say')}</option>
                </select>
              </div>
            </div>

            {/* Experience & Business Name */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Award size={14} className="text-primary-500" /> {t('Years of Experience')}
                </label>
                <input
                  type="number"
                  placeholder="e.g. 5"
                  min="0"
                  max="50"
                  value={formData.experienceYears}
                  onChange={(e) => setFormData(prev => ({ ...prev, experienceYears: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Briefcase size={14} className="text-primary-500" /> {t('Business / Trade Name')}
                </label>
                <input
                  type="text"
                  placeholder="e.g. Rahul Plumbing Co."
                  value={formData.businessName}
                  onChange={(e) => setFormData(prev => ({ ...prev, businessName: e.target.value }))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors"
                />
              </div>
            </div>

            {/* Bio */}
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <FileText size={14} className="text-primary-500" /> {t('About You / Bio')}
              </label>
              <textarea
                rows={4}
                placeholder={t('Tell customers about your skills, experience, and what makes you stand out…')}
                value={formData.bio}
                onChange={(e) => setFormData(prev => ({ ...prev, bio: e.target.value }))}
                maxLength={300}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 transition-colors resize-none"
              />
              <p className="text-xs text-gray-400 text-right">{formData.bio.length}/300 characters</p>
            </div>

            {/* Work Gallery & Experience Photos */}
            <div className="space-y-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-gray-900 flex items-center gap-2">
                    <ImageIcon size={18} className="text-primary-500" /> {t('Work Gallery & Portfolio')}
                  </h4>
                  <p className="text-xs text-gray-500">{t('Upload photos of your past work for customers to see.')}</p>
                </div>
                <label className="bg-primary-50 text-primary-600 px-4 py-2 rounded-xl text-xs font-bold cursor-pointer hover:bg-primary-100 transition-colors flex items-center gap-2">
                  <Upload size={14} /> {t('Add Photo')}
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleGalleryUpload(e.target.files[0])}
                  />
                </label>
              </div>

              {formData.workGallery.length > 0 ? (
                <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
                  {formData.workGallery.map((img) => (
                    <div key={img.id} className="relative aspect-square rounded-xl overflow-hidden group border border-gray-100">
                      <img src={img.preview} alt="Work" className="w-full h-full object-cover" />
                      <button
                        onClick={() => setFormData(prev => ({ ...prev, workGallery: prev.workGallery.filter(g => g.id !== img.id) }))}
                        className="absolute top-1 right-1 bg-red-500 text-white p-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-md"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 border-2 border-dashed border-gray-100 rounded-2xl text-center">
                  <p className="text-sm text-gray-400">{t('No work photos added yet.')}</p>
                </div>
              )}
            </div>

            {/* Required notice */}
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <span className="text-red-500">*</span> {t('Required fields')}
            </p>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">Step 2: Base Location Selection</h3>
            <p className="text-gray-600 text-sm">Click on the map to set your business base location or use your current location.</p>
            <div className="h-96 rounded-xl overflow-hidden border-2 border-primary-100 shadow-inner">
              <MapContainer center={formData.location} zoom={13} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <LocationMarker />
              </MapContainer>
            </div>
            <div className="flex items-center justify-between bg-primary-50 p-4 rounded-xl border border-primary-200">
              <div>
                <p className="text-sm font-bold text-primary-900">Current Location</p>
                <p className="text-xs text-primary-700">Lat: {formData.location.lat.toFixed(4)}, Lng: {formData.location.lng.toFixed(4)}</p>
              </div>
              <button 
                onClick={() => {
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                      (pos) => {
                        const newLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                        setFormData(prev => ({ ...prev, location: newLocation }));
                        toast.success('Location updated to your current position!');
                      },
                      (error) => {
                        toast.error('Unable to get location. Please enable location services or check browser permissions.');
                        console.error('Geolocation error:', error);
                      }
                    );
                  } else {
                    toast.error('Geolocation is not supported by your browser.');
                  }
                }}
                className="flex items-center space-x-2 bg-primary text-white px-6 py-3 rounded-xl font-bold hover:bg-primary-dark transition-all shadow-md hover:scale-105"
              >
                <MapPin size={18} />
                <span>Use Current Location</span>
              </button>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">Step 3: Service Area Definition</h3>
            <div className="flex space-x-4 mb-4">
              <button 
                onClick={() => setFormData(prev => ({ ...prev, serviceAreaType: 'radius' }))}
                className={`flex-1 py-2 rounded-lg font-medium border-2 ${formData.serviceAreaType === 'radius' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}`}
              >
                Radius Mode
              </button>
              <button 
                onClick={() => setFormData(prev => ({ ...prev, serviceAreaType: 'polygon' }))}
                className={`flex-1 py-2 rounded-lg font-medium border-2 ${formData.serviceAreaType === 'polygon' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}`}
              >
                Polygon Mode
              </button>
            </div>
            
            <div className="h-80 rounded-xl overflow-hidden border-2 border-primary-100">
              <MapContainer center={formData.location} zoom={11} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {formData.serviceAreaType === 'radius' ? (
                  <Circle center={formData.location} radius={formData.radius * 1609.34} color="purple" />
                ) : (
                  <PolygonSelector />
                )}
                <Marker position={formData.location} />
              </MapContainer>
            </div>

            {formData.serviceAreaType === 'radius' ? (
              <div className="p-4 bg-white rounded-lg border shadow-sm">
                <label className="block text-sm font-medium mb-2">Coverage Radius: {formData.radius} miles</label>
                <input 
                  type="range" min="1" max="50" value={formData.radius}
                  onChange={(e) => setFormData(prev => ({ ...prev, radius: parseInt(e.target.value) }))}
                  className="w-full accent-primary-500"
                />
              </div>
            ) : (
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600">Click on map to draw your custom service boundary.</p>
                <button 
                  onClick={() => setFormData(prev => ({ ...prev, polygonPoints: [] }))}
                  className="text-xs text-red-600 font-medium underline"
                >
                  Reset Polygon
                </button>
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-bold">Step 4: Service Categories</h3>
            {isAiLoading ? (
              <div className="flex flex-col items-center py-12 space-y-4">
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin" />
                <p className="text-gray-600 animate-pulse">AI is analyzing local demand trends...</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {allCategories.map(cat => (
                  <button
                    key={cat.value}
                    onClick={() => {
                      setFormData(prev => ({
                        ...prev,
                        categories: prev.categories.includes(cat.value) 
                          ? prev.categories.filter(c => c !== cat.value)
                          : [...prev.categories, cat.value]
                      }));
                    }}
                    className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                      formData.categories.includes(cat.value) ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                    }`}
                  >
                    {formData.suggestedCategories.includes(cat.value) && (
                      <span className="absolute top-2 right-2 flex items-center bg-yellow-400 text-[10px] font-bold px-1.5 py-0.5 rounded text-white uppercase">
                        AI Recommended
                      </span>
                    )}
                    <span className="text-2xl mb-2 block">{cat.icon}</span>
                    <span className="font-bold">{cat.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        );

      case 5:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-bold">Step 5: Identity Verification</h3>

            {/* Aadhar / PAN Verification */}
            <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
              <h4 className="font-bold text-gray-900 mb-4">1. Document Details</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-gray-700">Document Type</label>
                  <select
                    value={formData.documents.idType}
                    onChange={(e) => setFormData(prev => ({ ...prev, documents: { ...prev.documents, idType: e.target.value as any } }))}
                    disabled={formData.documents.isIdVerified}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 bg-white disabled:opacity-50"
                  >
                    <option value="aadhar">Aadhaar Card</option>
                    <option value="pan">PAN Card</option>
                  </select>
                </div>
                <div className="md:col-span-2 space-y-1.5">
                  <label className="text-sm font-semibold text-gray-700">Document Number</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder={formData.documents.idType === 'aadhar' ? "e.g., 1234 5678 9012" : "e.g., ABCDE1234F"}
                      value={formData.documents.idNumber}
                      onChange={(e) => setFormData(prev => ({ ...prev, documents: { ...prev.documents, idNumber: e.target.value.toUpperCase() } }))}
                      disabled={formData.documents.isIdVerified}
                      className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400 disabled:opacity-50"
                    />
                    {!formData.documents.isIdVerified ? (
                      <button
                        onClick={() => {
                          const num = formData.documents.idNumber.replace(/\s/g, '');
                          const type = formData.documents.idType;
                          if (type === 'aadhar' && num.length !== 12) {
                            return toast.error("Aadhaar must be exactly 12 digits");
                          }
                          if (type === 'pan' && !/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(num)) {
                            return toast.error("Invalid PAN format (e.g. ABCDE1234F)");
                          }
                          
                          // Mock verification delay
                          toast.promise(
                            new Promise(resolve => setTimeout(resolve, 1500)),
                            {
                              loading: `Verifying ${type.toUpperCase()}...`,
                              success: () => {
                                setFormData(prev => ({ ...prev, documents: { ...prev.documents, isIdVerified: true } }));
                                return 'Document Verified Successfully!';
                              },
                              error: 'Verification Failed'
                            }
                          );
                        }}
                        className="bg-primary text-white px-6 py-3 rounded-xl font-bold shadow-md hover:bg-primary-dark transition-colors"
                      >
                        Verify
                      </button>
                    ) : (
                      <div className="bg-green-100 text-green-700 px-6 py-3 rounded-xl font-bold flex items-center gap-2 border border-green-200">
                        <CheckCircle size={18} /> Verified
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <h4 className="font-bold text-gray-900 mt-6 pt-6 border-t border-gray-100">2. Document Photos</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-semibold">Govt. ID Front</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('idFront', e.target.files[0])}
                  className="hidden"
                  id="idFront"
                />
                <label
                  htmlFor="idFront"
                  className="h-40 border-2 border-dashed rounded-xl flex flex-col items-center justify-center bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  {formData.documents.idFront ? (
                    <div className="text-center">
                      <CheckCircle className="text-green-500 mx-auto mb-2" />
                      <span className="text-xs text-green-600 font-bold">Uploaded</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="text-gray-400 mb-2" />
                      <span className="text-xs text-gray-500">Upload document</span>
                    </>
                  )}
                </label>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold">Govt. ID Back</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('idBack', e.target.files[0])}
                  className="hidden"
                  id="idBack"
                />
                <label
                  htmlFor="idBack"
                  className="h-40 border-2 border-dashed rounded-xl flex flex-col items-center justify-center bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  {formData.documents.idBack ? (
                    <div className="text-center">
                      <CheckCircle className="text-green-500 mx-auto mb-2" />
                      <span className="text-xs text-green-600 font-bold">Uploaded</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="text-gray-400 mb-2" />
                      <span className="text-xs text-gray-500">Upload document</span>
                    </>
                  )}
                </label>
              </div>
            </div>
            <div className="p-6 bg-primary-50 rounded-2xl border-2 border-primary-200">
              <div className="flex items-center space-x-4 mb-4">
                <div className="w-16 h-16 rounded-full bg-primary-500 flex items-center justify-center text-white">
                  <Camera size={32} />
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-primary-900">Liveness Selfie</h4>
                  <p className="text-sm text-primary-700">We'll use AI to match your face with your ID.</p>
                </div>
              </div>
              {showCamera ? (
                <div className="space-y-4">
                  <video ref={videoRef} autoPlay className="w-full rounded-xl" />
                  <canvas ref={canvasRef} className="hidden" />
                  <div className="flex gap-3">
                    <button
                      onClick={captureSelfie}
                      className="flex-1 bg-primary text-white px-6 py-3 rounded-xl font-bold hover:bg-primary-dark"
                    >
                      📸 Capture
                    </button>
                    <button
                      onClick={stopCamera}
                      className="px-6 py-3 rounded-xl font-bold border-2 border-gray-300 hover:bg-gray-100"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : formData.documents.selfie ? (
                <div className="text-center py-4">
                  <CheckCircle className="text-green-500 mx-auto mb-2" size={40} />
                  <p className="text-green-600 font-bold">Selfie Captured!</p>
                </div>
              ) : (
                <button
                  onClick={startCamera}
                  className="w-full bg-white text-primary-600 px-6 py-3 rounded-xl font-bold shadow-sm hover:shadow-md transition-all"
                >
                  Start Selfie Capture
                </button>
              )}
            </div>
          </div>
        );

      case 6:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-bold">Step 6: Background Check</h3>
            <div className="bg-white p-8 rounded-3xl border-2 border-primary-100 shadow-xl text-center">
              <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <Shield size={40} />
              </div>
              <h4 className="text-2xl font-bold mb-2">Powered by Checkr AI</h4>
              <p className="text-gray-600 mb-8 px-4">
                QuickServe requires a professional background check to ensure community safety. This typically takes 24-48 hours.
              </p>
              <div className="space-y-4 max-w-sm mx-auto">
                <div className="flex items-center space-x-3 text-left p-3 bg-gray-50 rounded-xl">
                  <CheckCircle className="text-green-500" size={20} />
                  <span className="text-sm font-medium">SSN Verification</span>
                </div>
                <div className="flex items-center space-x-3 text-left p-3 bg-gray-50 rounded-xl">
                  <CheckCircle className="text-green-500" size={20} />
                  <span className="text-sm font-medium">Criminal Record Check</span>
                </div>
                <div className="flex items-center space-x-3 text-left p-3 bg-gray-50 rounded-xl">
                  <CheckCircle className="text-green-500" size={20} />
                  <span className="text-sm font-medium">Identity Validation</span>
                </div>
              </div>
              <button className="mt-8 w-full bg-black text-white py-4 rounded-2xl font-bold shadow-lg hover:bg-gray-800 transition-colors">
                Authorize Background Check
              </button>
            </div>
          </div>
        );

      case 7:
        const selectedCategory = formData.categories[0] || 'painter';
        const questions = backendQuestions.length > 0 ? backendQuestions : (APTITUDE_TEST_DATA[selectedCategory] || APTITUDE_TEST_DATA['painter']);
        const currentQuestion = questions[currentQuestionIdx];

        return (
          <div className="space-y-6">
            <h3 className="text-2xl font-black text-primary-dark">Step 7: Proficiency Verification</h3>
            
            {!testActive && testAnswers.length === 0 ? (
              <div className="bg-primary-50 p-8 rounded-[32px] border-2 border-primary-200 text-center space-y-6">
                <div className="w-20 h-20 bg-primary-500 text-white rounded-3xl flex items-center justify-center mx-auto shadow-xl rotate-3">
                  {isLoadingBackendQuestions ? <Loader2 size={40} className="animate-spin" /> : <FileText size={40} />}
                </div>
                <div>
                  <h4 className="text-xl font-bold text-primary-900">Skill Aptitude Test: {selectedCategory.toUpperCase()}</h4>
                  <p className="text-primary-700 max-w-sm mx-auto mt-2">
                    Complete 5 quick questions to verify your professional knowledge and earn your trust badge.
                  </p>
                </div>
                <button 
                  onClick={startAssessment}
                  disabled={isLoadingBackendQuestions}
                  className="bg-primary-dark text-white px-10 py-4 rounded-2xl font-black hover:scale-105 transition-all shadow-lg disabled:opacity-50"
                >
                  {isLoadingBackendQuestions ? 'Loading...' : 'Start Assessment'}
                </button>
              </div>
            ) : testActive ? (
              <div className="bg-white p-8 rounded-[32px] border-2 border-gray-100 shadow-xl space-y-8 relative overflow-hidden">
                <div className="absolute top-0 left-0 h-2 bg-primary-500 transition-all duration-500" style={{ width: `${(currentQuestionIdx / questions.length) * 100}%` }} />
                
                <div className="flex justify-between items-start">
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-black text-primary uppercase tracking-widest bg-primary-50 px-3 py-1 rounded-full w-fit">
                      Question {currentQuestionIdx + 1} of 5
                    </span>
                    <span className={`text-sm font-bold ${timeLeft < 60 ? 'text-red-500 animate-pulse' : 'text-gray-500'}`}>
                      ⏱️ Time Left: {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                  <button 
                    onClick={() => speakText(`${t(currentQuestion.question)}. ${t('Options are')}: ${currentQuestion.options.map((o: string) => t(o)).join(', ')}`)}
                    className="p-3 bg-gray-50 text-gray-400 hover:text-primary rounded-xl transition-all"
                    title="Listen to question"
                  >
                    <Volume2 size={20} />
                  </button>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xl font-bold text-gray-900 leading-tight">
                    {t(currentQuestion.question)}
                  </h4>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {currentQuestion.options.map((opt: string, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => {
                        const newAnswers = [...testAnswers, idx];
                        setTestAnswers(newAnswers);
                        speakText(`${t('You selected')}: ${t(opt)}`);
                        
                        if (currentQuestionIdx < questions.length - 1) {
                          setCurrentQuestionIdx(idx => idx + 1);
                        } else {
                          // Calculate score
                          let correct = 0;
                          questions.forEach((q: any, i: number) => {
                            if (newAnswers[i] === q.answer) correct++;
                          });
                          const finalScore = Math.round((correct / questions.length) * 100);
                          setTestScore(finalScore);
                          setTestActive(false);
                          setTimerActive(false);
                          toast.success(`${t('Assessment complete!')} Score: ${finalScore}%`);
                        }
                      }}
                      className="p-5 text-left border-2 border-gray-100 rounded-2xl font-bold bg-gray-50 hover:border-primary-500 hover:bg-primary-50 transition-all flex items-center justify-between group"
                    >
                      <span>{t(opt)}</span>
                      <ChevronRight size={18} className="text-gray-300 group-hover:text-primary transition-all translate-x-2 group-hover:translate-x-0 opacity-0 group-hover:opacity-100" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-6 rounded-[32px] border-4 border-green-200 text-center space-y-4 shadow-2xl relative overflow-hidden max-w-lg mx-auto transform scale-95">
                {/* Decorative background elements */}
                <div className="absolute top-0 right-0 w-24 h-24 bg-green-200 rounded-bl-full opacity-50 mix-blend-multiply" />
                <div className="absolute bottom-0 left-0 w-20 h-20 bg-emerald-200 rounded-tr-full opacity-50 mix-blend-multiply" />
                
                {/* Official Verified Stamp */}
                <div className="absolute -top-2 -right-2 rotate-12 z-20">
                  <div className="border-4 border-red-600 rounded-full w-24 h-24 flex items-center justify-center bg-white/40 backdrop-blur-sm shadow-lg">
                    <div className="border-2 border-red-600 rounded-full w-[84px] h-[84px] flex flex-col items-center justify-center">
                      <span className="text-red-600 font-extrabold text-[10px] leading-none mb-1">OFFICIAL</span>
                      <div className="bg-red-600 text-white font-black text-xs px-1 rounded transform -rotate-2">VERIFIED</div>
                      <Star size={10} className="fill-red-600 text-red-600 mt-1" />
                    </div>
                  </div>
                </div>

                <div className="w-20 h-20 bg-green-500 text-white rounded-full flex items-center justify-center mx-auto shadow-xl ring-8 ring-green-100 mt-2 relative z-10">
                  <Award size={40} />
                </div>
                
                <div className="relative z-10 space-y-4">
                  <div>
                    <h4 className="text-2xl font-black text-green-900 uppercase tracking-wider">Provider Certificate</h4>
                    <p className="text-[10px] font-bold text-green-600 uppercase tracking-[0.2em] mt-0.5">QuickServe AI Professional Accreditation</p>
                  </div>

                  <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-5 text-left border border-white/50 shadow-sm">
                    <div className="flex items-center gap-4 mb-4 border-b border-green-100 pb-3">
                      <div className="w-14 h-14 rounded-xl bg-gray-200 overflow-hidden shrink-0 border-2 border-white shadow-sm">
                        {profilePhotoPreview ? (
                          <img src={profilePhotoPreview} alt="Profile" className="w-full h-full object-cover" />
                        ) : (
                          <User size={28} className="m-auto mt-3 text-gray-400" />
                        )}
                      </div>
                      <div>
                        <h5 className="text-lg font-black text-gray-900 leading-tight">{formData.fullName || 'Provider Name'}</h5>
                        <p className="text-emerald-600 font-bold flex items-center gap-1 text-xs"><CheckCircle size={12}/> Certified {selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1)} Professional</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-green-50/50 p-2.5 rounded-xl border border-green-100">
                        <p className="text-[10px] text-gray-400 font-black uppercase tracking-tighter">Assessment Score</p>
                        <p className="text-xl font-black text-green-700">{testScore}%</p>
                      </div>
                      <div className="bg-green-50/50 p-2.5 rounded-xl border border-green-100">
                        <p className="text-[10px] text-gray-400 font-black uppercase tracking-tighter">Experience</p>
                        <p className="text-xl font-black text-green-700">{formData.experienceYears || 0} Yrs</p>
                      </div>
                      <div className="bg-green-50/50 p-2.5 rounded-xl border border-green-100">
                        <p className="text-[10px] text-gray-400 font-black uppercase tracking-tighter">Initial Rating</p>
                        <p className="text-xl font-black text-yellow-600 flex items-center gap-1">5.0 <Star size={14} fill="currentColor" /></p>
                      </div>
                      <div className="bg-green-50/50 p-2.5 rounded-xl border border-green-100">
                        <p className="text-[10px] text-gray-400 font-black uppercase tracking-tighter">Verified Gallery</p>
                        <p className="text-xl font-black text-green-700">{formData.workGallery.length} Items</p>
                      </div>
                    </div>
                  </div>

                  <p className="text-[10px] text-green-700/70 max-w-sm mx-auto font-bold leading-relaxed">
                    This badge & certificate will be displayed on your profile to verify your expertise and background.
                  </p>
                </div>

                <div className="flex flex-col items-center gap-2">
                  <button 
                    onClick={() => {
                      if (window.confirm("Are you sure you want to retake the test? Your current certificate will be replaced.")) {
                        setTestActive(true);
                        setTestAnswers([]);
                        setCurrentQuestionIdx(0);
                        setTimeLeft(360);
                        setTimerActive(true);
                        setTestScore(null);
                      }
                    }}
                    className="text-green-700 font-black text-sm underline hover:text-green-900 transition-colors py-1"
                  >
                    Retake Assessment
                  </button>
                </div>
              </div>
            )}
            
            <div className="p-6 bg-purple-50 rounded-[32px] border-2 border-purple-100 flex items-center gap-6">
              <div className="w-12 h-12 bg-purple-500 text-white rounded-2xl flex items-center justify-center shrink-0">
                <Volume2 size={24} />
              </div>
              <p className="text-sm text-purple-700 leading-relaxed">
                <span className="font-bold">Audio Accessibility:</span> If you prefer to hear the questions, click the speaker icon. Our AI will read each question and option aloud for you.
              </p>
            </div>
          </div>
        );

      case 8:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-bold">Step 8: Pricing & AI Assistant</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-white rounded-2xl border shadow-sm">
                <label className="text-xs font-bold uppercase text-gray-500 block mb-2">Hourly Rate ($)</label>
                <div className="flex items-center">
                  <DollarSign size={20} className="text-primary-500" />
                  <input 
                    type="number" placeholder="0.00" 
                    value={formData.hourlyRate}
                    onChange={e => setFormData(prev => ({ ...prev, hourlyRate: e.target.value }))}
                    className="w-full text-2xl font-bold focus:outline-none" 
                  />
                </div>
              </div>
              <div className="p-4 bg-white rounded-2xl border shadow-sm">
                <label className="text-xs font-bold uppercase text-gray-500 block mb-2">Emergency ($/hr)</label>
                <div className="flex items-center">
                  <DollarSign size={20} className="text-red-500" />
                  <input 
                    type="number" placeholder="0.00" 
                    value={formData.emergencyRate}
                    onChange={e => setFormData(prev => ({ ...prev, emergencyRate: e.target.value }))}
                    className="w-full text-2xl font-bold focus:outline-none" 
                  />
                </div>
              </div>
            </div>

            <div className={`p-6 rounded-3xl border-2 transition-all ${formData.aiBotEnabled ? 'border-primary-500 bg-primary-50' : 'border-gray-200 bg-gray-50'}`}>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="text-lg font-bold">QuickServe AI Service Bot</h4>
                  <p className="text-sm text-gray-600">Auto-booking, smart scheduling & pricing aggression.</p>
                </div>
                <div 
                  onClick={() => setFormData(prev => ({ ...prev, aiBotEnabled: !prev.aiBotEnabled }))}
                  className={`w-14 h-8 rounded-full relative cursor-pointer transition-colors ${formData.aiBotEnabled ? 'bg-primary-500' : 'bg-gray-300'}`}
                >
                  <div className={`w-6 h-6 bg-white rounded-full absolute top-1 transition-all ${formData.aiBotEnabled ? 'right-1' : 'left-1'}`} />
                </div>
              </div>

              {formData.aiBotEnabled && (
                <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase">Pricing Aggression</label>
                    <div className="flex p-1 bg-white rounded-xl border">
                      {['conservative', 'balanced', 'aggressive'].map(lvl => (
                        <button
                          key={lvl}
                          onClick={() => setFormData(prev => ({ ...prev, aiAggression: lvl as any }))}
                          className={`flex-1 py-1.5 rounded-lg text-xs font-bold capitalize transition-all ${
                            formData.aiAggression === lvl ? 'bg-primary-500 text-white' : 'text-gray-500'
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-3xl text-white shadow-xl">
              <h4 className="font-bold flex items-center space-x-2 mb-2">
                <Star size={18} className="fill-yellow-400 text-yellow-400" />
                <span>AI Launch Plan Ready!</span>
              </h4>
              <p className="text-xs opacity-90 leading-relaxed">
                Based on your profile, we've generated a 30-day launch strategy including peak hour optimization and competitive pricing tiers for your area.
              </p>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFA] pt-28 pb-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex items-center space-x-3 mb-6">
            <div className="w-14 h-14 bg-primary-dark rounded-2xl flex items-center justify-center text-white shadow-2xl">
              <Briefcase size={32} />
            </div>
            <h1 className="text-4xl font-black text-primary-dark tracking-tight">{t('Provider Onboarding')}</h1>
          </div>
          <p className="text-xl text-gray-500 font-bold uppercase tracking-widest max-w-2xl mx-auto">
            {t('Join the elite network of QuickServe professionals.')}
          </p>
        </div>

        {/* Multi-step progress bar */}
        <div className="mb-12 overflow-x-auto pb-4 scrollbar-hidden">
          <div className="flex justify-between items-start min-w-[800px] px-4">
            {steps.map((step) => (
              <div key={step.number} className="flex flex-col items-center relative flex-1">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-all duration-500 z-10 shadow-lg ${
                  currentStep >= step.number ? 'bg-primary text-white scale-110' : 'bg-white text-gray-400 border-2 border-gray-100'
                }`}>
                  <step.icon size={24} />
                </div>
                <div className="text-center px-2">
                  <p className={`text-xs font-black uppercase tracking-widest mb-1 ${
                    currentStep >= step.number ? 'text-primary-dark' : 'text-gray-400'
                  }`}>Step {step.number}</p>
                  <p className={`text-sm font-bold ${
                    currentStep >= step.number ? 'text-primary' : 'text-gray-400'
                  }`}>{step.title}</p>
                </div>
                {step.number < steps.length && (
                  <div className={`absolute top-7 left-[calc(50%+28px)] w-[calc(100%-56px)] h-1 transition-all duration-500 rounded-full ${
                    currentStep > step.number ? 'bg-primary shadow-[0_0_10px_rgba(13,122,127,0.3)]' : 'bg-gray-100'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content Card */}
        <div className="bg-white rounded-[40px] shadow-2xl shadow-primary-900/5 p-8 md:p-14 min-h-[600px] flex flex-col border border-gray-100/50">
          <div className="flex-1">
            {renderStep()}
          </div>

          <div className="mt-12 flex justify-between items-center pt-8 border-t border-gray-50">
            <button 
              onClick={handleBack}
              disabled={currentStep === 1}
              className="flex items-center space-x-3 text-gray-400 font-black text-lg hover:text-primary-dark disabled:opacity-0 transition-all px-6 py-2 rounded-xl"
            >
              <ChevronLeft size={24} />
              <span>{t('Previous')}</span>
            </button>
            
            {currentStep === steps.length ? (
              <button 
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="bg-primary-accent hover:bg-primary-dark text-white px-12 py-4 rounded-2xl font-black text-xl shadow-xl shadow-primary/20 flex items-center space-x-3 transition-all hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={24} className="animate-spin" />
                    <span>Creating Account…</span>
                  </>
                ) : (
                  <>
                    <span>Launch My Business</span>
                    <ChevronRight size={24} />
                  </>
                )}
              </button>
            ) : (
              <button 
                onClick={handleNext}
                className="bg-primary hover:bg-primary-dark text-white px-12 py-4 rounded-2xl font-black text-xl shadow-xl shadow-primary/20 flex items-center space-x-3 transition-all hover:scale-[1.02]"
              >
                <span>{t('Continue')}</span>
                <ChevronRight size={24} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProviderOnboarding;
