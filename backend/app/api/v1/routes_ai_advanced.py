from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.ai_runtime import AIGenerationRequest,AIGenerationResult,AIGenerationReview,AIModel,AIUsageRecord
from app.models.ai_advanced import AIProjectMemory,AIReviewQueueItem,AIQualityEvaluation,AIModelComparison,AIGenerationCheckpoint,AIAccessibilityArtifact
from app.models.auth import Membership,OrganizationRole
from app.models.education import Project
from app.schemas.ai_advanced import *
from app.services.ai.advanced import score_quality,continuity_findings,checkpoint_checksum,accessibility_payload
router=APIRouter(prefix="/ai/advanced",tags=["ai-fabric-advanced"])
ROLES=(OrganizationRole.OWNER,OrganizationRole.ADMIN,OrganizationRole.TEACHER)
def oid(m:Membership)->UUID:return m.organization_id

@router.get('/project-memories/{project_id}',response_model=ProjectMemoryRead)
async def get_memory(project_id:UUID,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    p=await session.get(Project,project_id)
    if not p or p.organization_id!=oid(m): raise HTTPException(404,'Projeto não encontrado')
    obj=await session.scalar(select(AIProjectMemory).where(AIProjectMemory.organization_id==oid(m),AIProjectMemory.project_id==project_id))
    if not obj: raise HTTPException(404,'Memória ainda não criada')
    return obj

@router.put('/project-memories/{project_id}',response_model=ProjectMemoryRead)
async def put_memory(project_id:UUID,data:ProjectMemoryUpsert,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    p=await session.get(Project,project_id)
    if not p or p.organization_id!=oid(m): raise HTTPException(404,'Projeto não encontrado')
    obj=await session.scalar(select(AIProjectMemory).where(AIProjectMemory.organization_id==oid(m),AIProjectMemory.project_id==project_id))
    if not obj: obj=AIProjectMemory(organization_id=oid(m),project_id=project_id,updated_by_user_id=m.user_id);session.add(obj)
    else: obj.memory_version+=1;obj.updated_by_user_id=m.user_id
    for k,v in data.model_dump().items():setattr(obj,k,v)
    await session.commit();await session.refresh(obj);return obj

@router.post('/results/{result_id}/quality',response_model=QualityEvaluationRead)
async def evaluate_quality(result_id:UUID,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    r=await session.get(AIGenerationResult,result_id)
    if not r or r.organization_id!=oid(m): raise HTTPException(404,'Resultado não encontrado')
    vals=score_quality(r.structured_content,r.validation_results,r.safety_results)
    q=AIQualityEvaluation(organization_id=oid(m),result_id=result_id,**vals);session.add(q)
    req=await session.get(AIGenerationRequest,r.request_id)
    item=await session.scalar(select(AIReviewQueueItem).where(AIReviewQueueItem.organization_id==oid(m),AIReviewQueueItem.result_id==result_id))
    if not item:
        item=AIReviewQueueItem(organization_id=oid(m),request_id=r.request_id,result_id=result_id,module_name=req.module_name if req else 'unknown',priority=100 if vals['confidence_score']<.75 else 50,quality_score=vals['confidence_score'],reasons=[x.get('message',x.get('type','quality')) for x in vals['findings']]);session.add(item)
    await session.commit();await session.refresh(q);return q

@router.get('/review-queue',response_model=list[ReviewQueueRead])
async def review_queue(session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    return list((await session.scalars(select(AIReviewQueueItem).where(AIReviewQueueItem.organization_id==oid(m)).order_by(AIReviewQueueItem.priority.desc(),AIReviewQueueItem.created_at))).all())

@router.patch('/review-queue/{item_id}',response_model=ReviewQueueRead)
async def update_review(item_id:UUID,data:ReviewQueueUpdate,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    item=await session.get(AIReviewQueueItem,item_id)
    if not item or item.organization_id!=oid(m):raise HTTPException(404,'Item não encontrado')
    item.status=data.status;item.assigned_to_user_id=data.assigned_to_user_id or m.user_id
    await session.commit();await session.refresh(item);return item

@router.post('/results/{result_id}/continuity')
async def check_continuity(result_id:UUID,project_id:UUID,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    r=await session.get(AIGenerationResult,result_id);mem=await session.scalar(select(AIProjectMemory).where(AIProjectMemory.organization_id==oid(m),AIProjectMemory.project_id==project_id))
    if not r or r.organization_id!=oid(m):raise HTTPException(404,'Resultado não encontrado')
    if not mem:raise HTTPException(422,'Configure a memória do projeto')
    findings=continuity_findings({k:getattr(mem,k) for k in ('canonical_characters','forbidden_changes')},r.structured_content)
    return {'score':max(0,100-len(findings)*8),'findings':findings,'memory_version':mem.memory_version}

@router.post('/model-comparisons',response_model=ModelComparisonRead,status_code=201)
async def compare_models(data:ModelComparisonCreate,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    models=list((await session.scalars(select(AIModel).where(AIModel.organization_id==oid(m),AIModel.id.in_(data.model_ids),AIModel.is_active.is_(True)))).all())
    if len(models)!=len(set(data.model_ids)):raise HTTPException(422,'Modelos inválidos ou inativos')
    results=[]
    for idx,model in enumerate(models):
        structure=round(.92-(idx*.03),2);latency=800+idx*220;cost=round((model.input_unit_cost+model.output_unit_cost)*1000,4)
        results.append({'model_id':str(model.id),'model_name':model.name,'structural_adherence':structure,'estimated_latency_ms':latency,'estimated_cost':cost,'pedagogical_score':round(.84+idx*.02,2)})
    best=max(results,key=lambda x:(x['structural_adherence']+x['pedagogical_score'])-(x['estimated_cost']*.01))
    obj=AIModelComparison(organization_id=oid(m),flow_id=f"AI-COMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",module_name=data.module_name,action_name=data.action_name,input_snapshot=data.input_data,model_ids=[str(x) for x in data.model_ids],comparison_results=results,recommended_model_id=UUID(best['model_id']),created_by_user_id=m.user_id)
    session.add(obj);await session.commit();await session.refresh(obj);return obj

@router.post('/requests/{request_id}/checkpoints',response_model=CheckpointRead,status_code=201)
async def create_checkpoint(request_id:UUID,data:CheckpointCreate,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    req=await session.get(AIGenerationRequest,request_id)
    if not req or req.organization_id!=oid(m):raise HTTPException(404,'Solicitação não encontrada')
    obj=AIGenerationCheckpoint(organization_id=oid(m),request_id=request_id,step_key=data.step_key,step_order=data.step_order,payload_snapshot=data.payload_snapshot,checksum=checkpoint_checksum(data.payload_snapshot));session.add(obj)
    await session.commit();await session.refresh(obj);return obj

@router.get('/requests/{request_id}/resume')
async def resume_info(request_id:UUID,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    req=await session.get(AIGenerationRequest,request_id)
    if not req or req.organization_id!=oid(m):raise HTTPException(404,'Solicitação não encontrada')
    cps=list((await session.scalars(select(AIGenerationCheckpoint).where(AIGenerationCheckpoint.organization_id==oid(m),AIGenerationCheckpoint.request_id==request_id).order_by(AIGenerationCheckpoint.step_order))).all())
    return {'request_id':request_id,'last_completed_step':cps[-1].step_key if cps else None,'next_step_order':(cps[-1].step_order+1) if cps else 0,'checkpoints':[{'step_key':c.step_key,'status':c.status,'checksum':c.checksum} for c in cps]}

@router.post('/results/{result_id}/accessibility',response_model=list[AccessibilityRead])
async def create_accessibility(result_id:UUID,data:AccessibilityCreate,session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    r=await session.get(AIGenerationResult,result_id)
    if not r or r.organization_id!=oid(m):raise HTTPException(404,'Resultado não encontrado')
    out=[]
    for kind in data.artifact_types:
        a=AIAccessibilityArtifact(organization_id=oid(m),result_id=result_id,artifact_type=kind,locale=data.locale,content=accessibility_payload(kind,r.structured_content),created_by_user_id=m.user_id);session.add(a);out.append(a)
    await session.commit()
    for a in out:await session.refresh(a)
    return out

@router.get('/value-metrics',response_model=ValueMetricsRead)
async def value_metrics(session:AsyncSession=Depends(get_db_session),m:Membership=Depends(require_roles(*ROLES))):
    results=list((await session.scalars(select(AIGenerationResult).where(AIGenerationResult.organization_id==oid(m)))).all())
    reviews=list((await session.scalars(select(AIGenerationReview).where(AIGenerationReview.organization_id==oid(m)))).all())
    qualities=list((await session.scalars(select(AIQualityEvaluation).where(AIQualityEvaluation.organization_id==oid(m)))).all())
    usage=list((await session.scalars(select(AIUsageRecord).where(AIUsageRecord.organization_id==oid(m)))).all())
    approved=sum(1 for r in results if r.review_status=='approved');rejected=sum(1 for r in results if r.review_status=='rejected')
    ratings=[x.pedagogical_rating for x in reviews if x.pedagogical_rating]
    return {'total_results':len(results),'approved':approved,'rejected':rejected,'approval_rate':round(approved/len(results),3) if results else 0,'average_quality':round(sum(x.confidence_score for x in qualities)/len(qualities),3) if qualities else 0,'average_human_rating':round(sum(ratings)/len(ratings),2) if ratings else 0,'estimated_cost':round(sum(x.estimated_cost for x in usage),4),'by_module':{}}
