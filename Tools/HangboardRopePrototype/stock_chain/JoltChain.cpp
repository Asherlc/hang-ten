// Isolated stock-engine diagnostic. No app dependency or acceptance override.
#include <Jolt/Jolt.h>
#include <Jolt/RegisterTypes.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Core/JobSystemSingleThreaded.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>
#include <Jolt/Physics/Body/MotionProperties.h>
#include <Jolt/Physics/Collision/Shape/MeshShape.h>
#include <Jolt/Physics/Collision/Shape/CapsuleShape.h>
#include <Jolt/Physics/Collision/GroupFilterTable.h>
#include <Jolt/Physics/Collision/ContactListener.h>
#include <Jolt/Physics/Constraints/PointConstraint.h>
#include "json.hpp"
#include <fstream>
#include <iostream>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <cstdarg>
using namespace JPH;
using json=nlohmann::json;
using Clock=std::chrono::steady_clock;
static void trace(const char*fmt,...){va_list args;va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);fputc('\n',stderr);}
static double seconds(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
static double units=1000;
static bool installExactInertia=false;
static RVec3 point(const json&j){return RVec3(j[0].get<double>()*units,j[1].get<double>()*units,j[2].get<double>()*units);}
static Vec3 vec(const json&j){return Vec3(float(j[0].get<double>()*units),float(j[1].get<double>()*units),float(j[2].get<double>()*units));}
static json arr(RVec3Arg p){return json::array({p.GetX()/units,p.GetY()/units,p.GetZ()/units});}
static json arrv(Vec3Arg p){return json::array({p.GetX()/units,p.GetY()/units,p.GetZ()/units});}
class BP final:public BroadPhaseLayerInterface{
public:uint GetNumBroadPhaseLayers()const override{return 1;}
BroadPhaseLayer GetBroadPhaseLayer(ObjectLayer)const override{return BroadPhaseLayer(0);}
};
class OP final:public ObjectVsBroadPhaseLayerFilter{public:bool ShouldCollide(ObjectLayer,BroadPhaseLayer)const override{return true;}};
class PP final:public ObjectLayerPairFilter{public:bool ShouldCollide(ObjectLayer,ObjectLayer)const override{return true;}};
class Contacts final:public ContactListener{
public:
    BodyID board;uint wood=0,rope=0;
    void OnContactAdded(const Body&a,const Body&b,const ContactManifold&,ContactSettings&)override{
        if(a.GetID()==board||b.GetID()==board)++wood;else ++rope;
    }
};
static void common(BodyCreationSettings&s){
    s.mFriction=0;s.mRestitution=0;s.mLinearDamping=0;s.mAngularDamping=0;
    s.mGravityFactor=0;s.mAllowSleeping=false;s.mMotionQuality=EMotionQuality::LinearCast;
    s.mMaxLinearVelocity=float(500*units);
}
struct Link{Body*body;double length;};
static RVec3 end(const Link&l,int sign){return l.body->GetPosition()+l.body->GetRotation()*Vec3(0,float(sign*l.length/2),0);}
static json simulate(const json&source,const json&descriptor){
    const double dt=1.0/240,damp=std::exp(-18*dt);
    auto begin=Clock::now();
    BP bp;OP op;PP pp;PhysicsSystem physics;
    physics.Init(2048,0,65536,65536,bp,op,pp);physics.SetGravity(Vec3::sZero());
    PhysicsSettings settings;settings.mConstraintWarmStart=false;
    settings.mPenetrationSlop=float(1e-5*units);settings.mSpeculativeContactDistance=float(5e-5*units);
    settings.mManifoldTolerance*=float(units);settings.mMaxPenetrationDistance*=float(units);
    settings.mBodyPairCacheMaxDeltaPositionSq*=float(units*units);
    settings.mContactPointPreserveLambdaMaxDistSq*=float(units*units);
    settings.mInternalEdgeRemovalVertexToleranceSq*=float(units*units);
    settings.mMinVelocityForRestitution*=float(units);settings.mPointVelocitySleepThreshold*=float(units);
    physics.SetPhysicsSettings(settings);
    BodyInterface&bi=physics.GetBodyInterface();
    VertexList vertices;IndexedTriangleList triangles;
    for(auto&v:descriptor["collision"]["vertices"]){Vec3 p=vec(v);vertices.push_back(Float3(p.GetX(),p.GetY(),p.GetZ()));}
    for(auto&t:descriptor["collision"]["triangles"])triangles.emplace_back(t[0].get<uint>(),t[1].get<uint>(),t[2].get<uint>());
    MeshShapeSettings mesh(vertices,triangles);
    auto meshResult=mesh.Create();if(meshResult.HasError())throw std::runtime_error(meshResult.GetError().c_str());
    auto q=source["orientation"];
    Quat oldq(q[0].get<float>(),q[1].get<float>(),q[2].get<float>(),q[3].get<float>());
    const Quat target=Quat::sRotation(Vec3::sAxisZ(),float(JPH_PI/2));
    double dot=0;for(int k=0;k<4;++k)dot+=q[k].get<double>()*(k==2||k==3?std::sqrt(0.5):0);
    double angle=2*std::acos(std::min(1.0,std::abs(dot)));
    Quat nextq=oldq.SLERP(target,float(std::min(1.0,dt*2.1/angle)));
    BodyCreationSettings boardSettings(meshResult.Get(),RVec3(0,source["boardHeight"].get<double>()*units,0),nextq,EMotionType::Dynamic,0);
    common(boardSettings);boardSettings.mAllowedDOFs=EAllowedDOFs::TranslationY;
    boardSettings.mOverrideMassProperties=EOverrideMassProperties::MassAndInertiaProvided;
    boardSettings.mMassPropertiesOverride.mMass=source["boardMass"].get<float>();
    boardSettings.mMassPropertiesOverride.mInertia=Mat44::sScale(Vec3::sReplicate(1));
    boardSettings.mLinearVelocity=Vec3(0,float((source["boardVerticalVelocity"].get<double>()-9.81*dt)*damp*units),0);
    Body*board=bi.CreateBody(boardSettings);if(!board)throw std::runtime_error("Board allocation failed");
    bi.AddBody(board->GetID(),EActivation::Activate);
    Contacts contacts;contacts.board=board->GetID();physics.SetContactListener(&contacts);
    std::vector<std::vector<Link>> ropes;
    json initial=json::array();
    for(size_t r=0;r<source["ropes"].size();++r){
        const auto&rope=source["ropes"][r];const auto&lengths=rope["restLengths"];
        uint count=uint(lengths.size());double radius=rope["radius"].get<double>();
        if(!rope["attachments"].empty())throw std::runtime_error("This bounded fixture does not support tied board attachments");
        Ref<GroupFilterTable>filter=new GroupFilterTable(count);
        std::vector<double>arc(1,0);for(auto&l:lengths)arc.push_back(arc.back()+l.get<double>());
        bool shared=rope["supports"].contains("0")&&rope["supports"].contains(std::to_string(count))&&point(rope["supports"]["0"])==point(rope["supports"][std::to_string(count)]);
        json excluded=json::array();
        for(uint i=0;i<count;++i)for(uint j=i+1;j<count;++j){
            bool adjacent=j==i+1,near=arc[j]-arc[i+1]<JPH_PI*radius;
            bool knot=shared&&std::min(arc[i],arc.back()-arc[i+1])<4*radius&&std::min(arc[j],arc.back()-arc[j+1])<4*radius;
            if(adjacent||near||knot){filter->DisableCollision(i,j);excluded.push_back({i,j});}
        }
        std::vector<Link>links;double mass=0,maxInitialError=0,maxInstalledError=0;
        json capsules=json::array();
        for(uint i=0;i<count;++i){
            double length=lengths[i].get<double>()*units;RVec3 a=point(rope["positions"][i]),b=point(rope["positions"][i+1]);
            Vec3 dir=Vec3(b-a).Normalized();Quat rotation=Quat::sFromTo(Vec3::sAxisY(),dir);
            BodyCreationSettings s(new CapsuleShape(float(length/2),float(radius*units)),(a+b)*0.5,rotation,EMotionType::Dynamic,0);
            common(s);s.mCollisionGroup=CollisionGroup(filter,uint(r),i);
            double m=rope["linearMass"].get<double>()*length/units,I=m*length*length/4;mass+=m;
            s.mOverrideMassProperties=EOverrideMassProperties::MassAndInertiaProvided;
            s.mMassPropertiesOverride.mMass=float(m);s.mMassPropertiesOverride.mInertia=Mat44::sScale(Vec3(float(I),float(I*1e-6),float(I)));
            Vec3 va=vec(rope["velocities"][i]),vb=vec(rope["velocities"][i+1]);
            auto predictor=[&](uint k,Vec3 v){return rope["supports"].contains(std::to_string(k))?Vec3::sZero():(v+Vec3(0,float(-9.81*dt*units),0))*float(damp);};
            va=predictor(i,va);vb=predictor(i+1,vb);
            s.mLinearVelocity=(va+vb)*0.5f;s.mAngularVelocity=dir.Cross(vb-va)/float(length);
            Body*body=bi.CreateBody(s);if(!body)throw std::runtime_error("Link allocation failed");
            // Validate the tensor Jolt actually installed; it silently substitutes
            // a unit sphere when the requested principal moments are too small.
            Vec3 expected(float(1/I),float(1/(I*1e-6)),float(1/I));
            if(installExactInertia)body->GetMotionProperties()->SetInverseInertia(expected,Quat::sIdentity());
            Mat44 actual=body->GetMotionProperties()->GetInverseInertiaForRotation(Mat44::sIdentity());
            double installedError=std::abs(double(body->GetMotionProperties()->GetInverseMass())*m-1);
            for(int column=0;column<3;++column)for(int row=0;row<3;++row){
                double e=column==row?expected[row]:0;
                installedError=std::max(installedError,std::abs(double(actual.GetColumn3(column)[row])-e)/expected[row]);
            }
            maxInstalledError=std::max(maxInstalledError,installedError);
            if(installedError>1e-5){
                std::cerr<<"units "<<units<<" link "<<i<<" I "<<I<<" expected inverse "<<expected.GetX()<<","<<expected.GetY()<<","<<expected.GetZ()<<" actual diagonal "<<actual.GetColumn3(0)[0]<<","<<actual.GetColumn3(1)[1]<<","<<actual.GetColumn3(2)[2]<<" relative error "<<installedError<<"\n";
                throw std::runtime_error("SETUP FAIL: installed mass/inertia differs from endpoint-lumped link model");
            }
            bi.AddBody(body->GetID(),EActivation::Activate);links.push_back({body,length});
            maxInitialError=std::max(maxInitialError,std::max((end(links.back(),-1)-a).Length(),(end(links.back(),1)-b).Length())/units);
            capsules.push_back({{"a",arr(end(links.back(),-1))},{"b",arr(end(links.back(),1))},{"mass",m}});
        }
        auto joint=[&](Body&first,Body&second,RVec3Arg p1,RVec3Arg p2){
            PointConstraintSettings ps;ps.mSpace=EConstraintSpace::LocalToBodyCOM;ps.mPoint1=p1;ps.mPoint2=p2;
            physics.AddConstraint(ps.Create(first,second));
        };
        for(uint i=1;i<count;++i)joint(*links[i-1].body,*links[i].body,RVec3(0,lengths[i-1].get<double>()*units/2,0),RVec3(0,-lengths[i].get<double>()*units/2,0));
        for(auto it=rope["supports"].begin();it!=rope["supports"].end();++it){
            uint index=uint(std::stoul(it.key()));if(index>count)throw std::runtime_error("Support out of range");
            if(index<count)joint(Body::sFixedToWorld,*links[index].body,point(it.value()),RVec3(0,-links[index].length/2,0));
            if(index>0)joint(Body::sFixedToWorld,*links[index-1].body,point(it.value()),RVec3(0,links[index-1].length/2,0));
        }
        if(maxInitialError>1e-8)throw std::runtime_error("Initial capsule endpoints do not reproduce checkpoint within 10 nm");
        initial.push_back({{"id",rope["id"]},{"capsules",capsules},{"excludedPairs",excluded},{"totalMass",mass},{"maxEndpointMappingError",maxInitialError},{"maxInstalledMassInertiaRelativeError",maxInstalledError}});
        ropes.push_back(std::move(links));
    }
    physics.OptimizeBroadPhase();double setup=seconds(begin);
    std::cerr<<"Imported "<<ropes.front().size()<<" capsules; beginning update\n";
    TempAllocatorImpl temp(128*1024*1024);JobSystemSingleThreaded jobs(cMaxPhysicsJobs);
    auto t=Clock::now();EPhysicsUpdateError error=physics.Update(float(dt),1,&temp,&jobs);double duration=seconds(t);
    json checkpoint=source;checkpoint["boardHeight"]=board->GetPosition().GetY()/units;checkpoint["boardVerticalVelocity"]=board->GetLinearVelocity().GetY()/units;
    double qnorm=std::sqrt(double(nextq.GetX())*nextq.GetX()+double(nextq.GetY())*nextq.GetY()+double(nextq.GetZ())*nextq.GetZ()+double(nextq.GetW())*nextq.GetW());
    checkpoint["orientation"]={nextq.GetX()/qnorm,nextq.GetY()/qnorm,nextq.GetZ()/qnorm,nextq.GetW()/qnorm};
    json output=json::array(),engineState=json::array();double gap=0;
    for(size_t r=0;r<ropes.size();++r){
        auto&links=ropes[r];auto&rope=checkpoint["ropes"][r];json capsules=json::array(),positions=json::array(),velocities=json::array();
        for(auto&l:links){
            capsules.push_back({{"a",arr(end(l,-1))},{"b",arr(end(l,1))}});
            Quat q=l.body->GetRotation();
            engineState.push_back({{"position",arr(l.body->GetPosition())},{"rotation",{q.GetX(),q.GetY(),q.GetZ(),q.GetW()}},
                {"linearVelocity",arrv(l.body->GetLinearVelocity())},{"angularVelocity",{l.body->GetAngularVelocity().GetX(),l.body->GetAngularVelocity().GetY(),l.body->GetAngularVelocity().GetZ()}}});
        }
        for(uint i=0;i<=links.size();++i){
            RVec3 p=i==0?end(links.front(),-1):i==links.size()?end(links.back(),1):(end(links[i-1],1)+end(links[i],-1))*0.5;
            if(i>0&&i<links.size())gap=std::max(gap,(end(links[i-1],1)-end(links[i],-1)).Length());
            if(rope["supports"].contains(std::to_string(i))){RVec3 fixed=point(rope["supports"][std::to_string(i)]);gap=std::max(gap,(p-fixed).Length());p=fixed;}
            positions.push_back(arr(p));velocities.push_back(arrv(Vec3((p-point(source["ropes"][r]["positions"][i]))/dt)));
        }
        rope["previousPositions"]=source["ropes"][r]["positions"];rope["positions"]=positions;rope["velocities"]=velocities;
        output.push_back({{"id",rope["id"]},{"capsules",capsules}});
    }
    return {{"checkpoint",checkpoint},{"initial",initial},{"actualCapsules",output},{"engineState",engineState},{"woodContactManifolds",contacts.wood},{"ropeContactManifolds",contacts.rope},{"jointEndpointGap",gap/units},{"unitsPerMetre",units},{"setupSeconds",setup},{"updateSeconds",duration},{"updateError",uint32(error)},
        {"settings",{{"velocitySteps",settings.mNumVelocitySteps},{"positionSteps",settings.mNumPositionSteps},{"dt",dt},{"warmStart",false},{"penetrationSlop",settings.mPenetrationSlop},{"speculativeContactDistance",settings.mSpeculativeContactDistance}}}};
}
int main(int argc,char**argv){
    if(argc!=6)return 2;
    units=std::stod(argv[4]);if(units!=1&&units!=1000)return 2;
    installExactInertia=std::string(argv[5])=="install";
    RegisterDefaultAllocator();Trace=trace;Factory::sInstance=new Factory();RegisterTypes();
    json source,descriptor;std::ifstream(argv[1])>>source;std::ifstream(argv[2])>>descriptor;
    json reports=json::array();for(int run=0;run<2;++run)reports.push_back(simulate(source,descriptor));
    std::ofstream(argv[3])<<reports.dump(2)<<"\n";
    for(auto&r:reports)std::cout<<"update "<<r["updateSeconds"]<<" s, joint gap "<<r["jointEndpointGap"]<<" m, error "<<r["updateError"]<<"\n";
    UnregisterTypes();delete Factory::sInstance;Factory::sInstance=nullptr;
}
