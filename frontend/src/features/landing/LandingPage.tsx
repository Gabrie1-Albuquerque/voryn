import {
  BarChart3,
  BellRing,
  CalendarCheck,
  CalendarDays,
  CheckCircle2,
  Dog,
  Globe,
  HeartPulse,
  Link2,
  Mail,
  MessageCircle,
  PhoneOff,
  QrCode,
  Scissors,
  Sparkles,
  Stethoscope,
  UserX,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import "./landing.css";

const WHATSAPP_URL =
  "https://wa.me/55489995217167?text=" +
  encodeURIComponent("Olá! Quero uma demonstração da plataforma de agendamentos.");

function WhatsAppCta({ large, children }: { large?: boolean; children: string }) {
  return (
    <a className={large ? "btn-whatsapp lg" : "btn-whatsapp"} href={WHATSAPP_URL} target="_blank" rel="noreferrer">
      <MessageCircle size={large ? 20 : 17} />
      {children}
    </a>
  );
}

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-header-inner">
          <a className="landing-brand" href="#">
            <span className="landing-brand-icon">
              <CalendarCheck size={19} />
            </span>
            Plataforma Inteligente de Agendamentos
          </a>
          <Link to="/login" className="ghost-link">
            Entrar
          </Link>
          <WhatsAppCta>Falar no WhatsApp</WhatsAppCta>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-container landing-hero-inner">
          <div>
            <span className="landing-eyebrow">
              <Sparkles size={15} />
              Agendamento inteligente para o seu negócio
            </span>
            <h1>
              Horário vazio é <span className="grad">dinheiro que não volta.</span>
            </h1>
            <p className="landing-hero-sub">
              Confirmação e lembretes automáticos no WhatsApp, página de agendamento aberta 24h e sinal via PIX antes
              do atendimento. Menos faltas, agenda cheia — e você no controle de tudo.
            </p>
            <div className="landing-hero-ctas">
              <WhatsAppCta large>Quero uma demonstração</WhatsAppCta>
              <Link to="/login" className="btn-ghost">
                Já sou cliente
              </Link>
            </div>
            <div className="landing-hero-trust">
              <span>
                <CheckCircle2 size={15} /> Sem instalar nada
              </span>
              <span>
                <CheckCircle2 size={15} /> Implantação assistida
              </span>
              <span>
                <CheckCircle2 size={15} /> Feito para o Brasil: WhatsApp + PIX
              </span>
            </div>
          </div>

          {/* Decorative product mock, built in CSS -- no fake screenshots */}
          <div className="hero-mock" aria-hidden="true">
            <div className="hero-mock-agenda">
              <div className="hero-mock-agenda-title">
                <CalendarDays size={15} />
                Agenda de hoje
              </div>
              <div className="hero-mock-slot a">
                <strong>09:00</strong> Corte — Maria S.
              </div>
              <div className="hero-mock-slot b">
                <strong>10:30</strong> Coloração — Juliana P.
              </div>
              <div className="hero-mock-slot c">
                <strong>14:00</strong> Barba — Carlos M.
              </div>
              <div className="hero-mock-slot a">
                <strong>16:00</strong> Escova — Fernanda L.
              </div>
            </div>
            <div className="hero-mock-chat">
              <div className="hero-mock-chat-title">
                <span className="wa-dot">
                  <MessageCircle size={14} />
                </span>
                WhatsApp
              </div>
              <div className="hero-bubble in">
                Oi, Maria! Lembrete: seu horário é <strong>amanhã às 14h</strong>. Responda <strong>1</strong> para
                confirmar ou <strong>2</strong> para cancelar.
              </div>
              <div className="hero-bubble out">1</div>
              <div className="hero-bubble status">
                <CheckCircle2 size={14} />
                Agendamento confirmado
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section alt">
        <div className="landing-container">
          <div className="landing-section-head">
            <h2>Você conhece esses prejuízos?</h2>
            <p>Todo negócio de agenda sofre com os mesmos três. A plataforma ataca cada um deles, no automático.</p>
          </div>
          <div className="landing-grid">
            <div className="landing-card">
              <div className="landing-card-icon">
                <UserX size={22} />
              </div>
              <span className="pain">Cliente marca e some</span>
              <h3>Lembrete + confirmação no WhatsApp</h3>
              <p>
                Lembrete automático 24h e 2h antes. O cliente confirma respondendo <strong>1</strong> — sem app, sem
                ligação, sem depender de ninguém lembrar.
              </p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <PhoneOff size={22} />
              </div>
              <span className="pain">Telefone o dia inteiro</span>
              <h3>Agendamento online 24h</h3>
              <p>
                Seu link próprio de agendamento: o cliente escolhe serviço, profissional e horário sozinho — inclusive
                domingo à noite, enquanto você descansa.
              </p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <QrCode size={22} />
              </div>
              <span className="pain">Desistência de última hora</span>
              <h3>Sinal via PIX no ato</h3>
              <p>
                Serviços que exigem sinal só confirmam depois que o PIX cai. Quem paga antecipado, aparece — e se não
                aparecer, o prejuízo não é só seu.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-container">
          <div className="landing-section-head">
            <h2>Como funciona</h2>
            <p>Quatro passos, e os três primeiros acontecem sem você tocar em nada.</p>
          </div>
          <div className="landing-steps">
            <div className="landing-step">
              <div className="landing-step-num">1</div>
              <h3>Cliente agenda pelo seu link</h3>
              <p>Página com a sua marca, serviços e horários reais — sem baixar aplicativo.</p>
            </div>
            <div className="landing-step">
              <div className="landing-step-num">2</div>
              <h3>O sistema confirma e lembra</h3>
              <p>Confirmação na hora e lembretes 24h e 2h antes, por WhatsApp e email.</p>
            </div>
            <div className="landing-step">
              <div className="landing-step-num">3</div>
              <h3>Sinal via PIX (se você quiser)</h3>
              <p>Por serviço, você decide: valor fixo ou percentual. O agendamento só confirma com o pagamento.</p>
            </div>
            <div className="landing-step">
              <div className="landing-step-num">4</div>
              <h3>Você acompanha no painel</h3>
              <p>Receita prevista e realizada, taxa de faltas, ocupação da equipe e serviços mais vendidos.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section alt">
        <div className="landing-container">
          <div className="landing-section-head">
            <h2>Os canais que o seu cliente já usa</h2>
            <p>Nada de obrigar ninguém a baixar mais um aplicativo.</p>
          </div>
          <div className="landing-grid">
            <div className="landing-card">
              <div className="landing-card-icon">
                <MessageCircle size={22} />
              </div>
              <h3>WhatsApp</h3>
              <p>Lembretes, confirmação com uma resposta ("1" confirma, "2" cancela) e aviso de reagendamento.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <Mail size={22} />
              </div>
              <h3>Email</h3>
              <p>Confirmações e avisos também por email, para clientes e para a sua própria equipe.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <Globe size={22} />
              </div>
              <h3>Sua página de agendamento</h3>
              <p>Um link seu, tipo <em>suaempresa</em> — para colocar no Instagram, no Google e no status do WhatsApp.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-container">
          <div className="landing-section-head">
            <h2>Tudo que o dia a dia pede</h2>
            <p>Da agenda ao caixa, num lugar só.</p>
          </div>
          <div className="landing-grid">
            <div className="landing-card">
              <div className="landing-card-icon">
                <CalendarDays size={22} />
              </div>
              <h3>Agenda visual</h3>
              <p>Dia, semana e mês. Arraste para reagendar — o sistema avisa o cliente sozinho.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <Users size={22} />
              </div>
              <h3>Clientes com histórico</h3>
              <p>Preferências, alertas (alergias, restrições) e anotações por atendimento, sempre à mão.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <BellRing size={22} />
              </div>
              <h3>Lista de espera automática</h3>
              <p>Cancelou? O sistema oferece o horário para quem estava esperando — sem você fazer nada.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <BarChart3 size={22} />
              </div>
              <h3>Dashboard gerencial</h3>
              <p>Receita, ocupação, taxa de faltas e ranking de serviços, por período.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <Users size={22} />
              </div>
              <h3>Equipe e salas</h3>
              <p>Vários profissionais, horários próprios e controle de salas/cadeiras sem choque de horário.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">
                <QrCode size={22} />
              </div>
              <h3>Sinal via PIX integrado</h3>
              <p>Cobrança de sinal via Mercado Pago, com confirmação automática do agendamento quando o PIX cai.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section alt">
        <div className="landing-container landing-vs">
          <div>
            <h2>Mais que um bot de agendamento</h2>
            <p>
              Bots de WhatsApp param na conversa. Aqui, a conversa é só o começo: por trás dela existe um sistema de
              gestão completo — porque confirmar horário não adianta se você não enxerga a agenda, o caixa e as faltas
              do mês.
            </p>
          </div>
          <ul className="landing-checklist">
            <li>
              <CheckCircle2 className="check" size={19} />
              Agenda visual completa, não só mensagens automáticas
            </li>
            <li>
              <CheckCircle2 className="check" size={19} />
              Sinal via PIX integrado ao agendamento, não um link solto
            </li>
            <li>
              <CheckCircle2 className="check" size={19} />
              Lista de espera que preenche horário vago sozinha
            </li>
            <li>
              <CheckCircle2 className="check" size={19} />
              Histórico e alertas por cliente, como uma ficha de verdade
            </li>
            <li>
              <CheckCircle2 className="check" size={19} />
              Números do negócio (receita, faltas, ocupação) num painel só
            </li>
          </ul>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-container">
          <div className="landing-section-head">
            <h2>Feito para quem vive de agenda</h2>
          </div>
          <div className="landing-segments">
            <span className="landing-segment">
              <Scissors size={16} /> Salões de beleza
            </span>
            <span className="landing-segment">
              <Scissors size={16} /> Barbearias
            </span>
            <span className="landing-segment">
              <Stethoscope size={16} /> Clínicas e consultórios
            </span>
            <span className="landing-segment">
              <HeartPulse size={16} /> Estética e bem-estar
            </span>
            <span className="landing-segment">
              <Dog size={16} /> Pet shops
            </span>
            <span className="landing-segment">
              <Link2 size={16} /> Estúdios e serviços com hora marcada
            </span>
          </div>
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="landing-container">
          <div className="landing-cta-band">
            <h2>Quanto custa um horário vazio na sua agenda?</h2>
            <p>Fale com a gente no WhatsApp e veja a plataforma funcionando com os serviços do seu negócio.</p>
            <WhatsAppCta large>Pedir demonstração no WhatsApp</WhatsAppCta>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <span>
            <strong>Plataforma Inteligente de Agendamentos</strong> — menos faltas, agenda cheia.
          </span>
          <span style={{ display: "flex", gap: 20 }}>
            <a href={WHATSAPP_URL} target="_blank" rel="noreferrer">
              WhatsApp: (48) 99952-17167
            </a>
            <Link to="/login">Entrar</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}
