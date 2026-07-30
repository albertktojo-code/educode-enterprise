import { useState } from "react";
import { comicPageEditorApi } from "./api";
import { LearningAnalyticsPanel } from "./LearningAnalyticsPanel";

interface Props { open:boolean; projectId:string; onClose:()=>void; }

export function DeliveryStudio({open,projectId,onClose}:Props){
  const [title,setTitle]=useState("HQ e atividades");
  const [targetId,setTargetId]=useState("");
  const [targetType,setTargetType]=useState("CLASS");
  const [startsAt,setStartsAt]=useState("");
  const [endsAt,setEndsAt]=useState("");
  const [maxAttempts,setMaxAttempts]=useState(1);
  const [duration,setDuration]=useState(60);
  const [deliveryId,setDeliveryId]=useState("");
  const [monitoring,setMonitoring]=useState("");
  const [message,setMessage]=useState("");
  const [busy,setBusy]=useState(false);
  const [analyticsOpen,setAnalyticsOpen]=useState(false);

  async function create(){
    setBusy(true);setMessage("");
    try{
      const result=await comicPageEditorApi.createActivityDelivery(projectId,{
        title,starts_at:new Date(startsAt).toISOString(),ends_at:new Date(endsAt).toISOString(),
        duration_minutes:duration,max_attempts:maxAttempts,navigation_mode:"FREE",
        shuffle_questions:false,shuffle_options:false,allow_resume:true,autosave_seconds:15,
        delivery_mode:"HQ_FLOW",reader_required:true,release_answer_key:"AFTER_SUBMISSION",
        access_settings:{keyboard_navigation:true},monitoring_settings:{show_live_progress:true},
        targets:[{target_type:targetType,target_id:targetId,extra_attempts:0}]
      });
      setDeliveryId(result.id);setMessage("Aplicação criada e agendada.");
    }catch(error){setMessage(error instanceof Error?error.message:"Falha ao criar aplicação.");}
    finally{setBusy(false);}
  }
  async function publish(){
    if(!deliveryId)return;setBusy(true);
    try{await comicPageEditorApi.publishActivityDelivery(deliveryId);setMessage("Aplicação publicada para o público selecionado.");}
    finally{setBusy(false);}
  }
  async function monitor(){
    if(!deliveryId)return;
    const result=await comicPageEditorApi.monitorActivityDelivery(deliveryId);
    setMonitoring(JSON.stringify(result,null,2));
  }
  if(!open)return null;
  return <>
    <LearningAnalyticsPanel
      open={analyticsOpen}
      deliveryId={deliveryId}
      onClose={()=>setAnalyticsOpen(false)}
    />
    <div className="delivery-studio-overlay" role="dialog" aria-modal="true">
    <section className="delivery-studio-dialog">
      <header><div><span className="hq-eyebrow">Sprint 16.11.2</span><h2>Aplicação para turmas e monitoramento</h2></div><button onClick={onClose}>Fechar</button></header>
      <div className="delivery-studio-grid">
        <section>
          <label>Título<input value={title} onChange={e=>setTitle(e.target.value)}/></label>
          <div className="delivery-row">
            <label>Público<select value={targetType} onChange={e=>setTargetType(e.target.value)}><option value="CLASS">Turma</option><option value="GROUP">Grupo</option><option value="STUDENT">Estudante</option></select></label>
            <label>ID do público<input value={targetId} onChange={e=>setTargetId(e.target.value)}/></label>
          </div>
          <div className="delivery-row">
            <label>Início<input type="datetime-local" value={startsAt} onChange={e=>setStartsAt(e.target.value)}/></label>
            <label>Fim<input type="datetime-local" value={endsAt} onChange={e=>setEndsAt(e.target.value)}/></label>
          </div>
          <div className="delivery-row">
            <label>Duração<input type="number" min={1} value={duration} onChange={e=>setDuration(Number(e.target.value))}/></label>
            <label>Tentativas<input type="number" min={1} value={maxAttempts} onChange={e=>setMaxAttempts(Number(e.target.value))}/></label>
          </div>
          <div className="delivery-actions">
            <button disabled={busy||!targetId||!startsAt||!endsAt} onClick={()=>void create()}>Criar aplicação</button>
            <button disabled={busy||!deliveryId} onClick={()=>void publish()}>Publicar</button>
            <button disabled={!deliveryId} onClick={()=>void monitor()}>Atualizar monitoramento</button>
            <button disabled={!deliveryId} onClick={()=>setAnalyticsOpen(true)}>Analytics pós-HQ</button>
            <button
              disabled={!deliveryId}
              onClick={() => {
                if (deliveryId) {
                  window.open(
                    `/student/hq-experience/${deliveryId}`,
                    "_blank",
                    "noopener,noreferrer",
                  );
                }
              }}
            >
              Abrir experiência do estudante
            </button>
          </div>
          {message?<p>{message}</p>:null}
        </section>
        <section><h3>Monitoramento</h3><pre>{monitoring||"Crie e publique uma aplicação para acompanhar o progresso."}</pre></section>
      </div>
    </section>
  </div>
  </>
}
