#include <btBulletDynamicsCommon.h>
#include <BulletDynamics/Featherstone/btMultiBody.h>
#include <BulletDynamics/Featherstone/btMultiBodyLinkCollider.h>
#include <BulletDynamics/Featherstone/btMultiBodyDynamicsWorld.h>
#include <BulletDynamics/Featherstone/btMultiBodyConstraintSolver.h>
#include <BulletDynamics/Featherstone/btMultiBodyPoint2Point.h>
#include <BulletCollision/Gimpact/btGImpactShape.h>
#include <BulletCollision/Gimpact/btGImpactCollisionAlgorithm.h>
#include "json.hpp"
#include <fstream>
#include <iostream>
#include <chrono>
#include <memory>
#include <cmath>
#include <stdexcept>
using json=nlohmann::json;
using Clock=std::chrono::steady_clock;
static double seconds(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
static btVector3 point(const json&j){return btVector3(j[0].get<double>(),j[1].get<double>(),j[2].get<double>());}
static json arr(const btVector3&p){return json::array({p.x(),p.y(),p.z()});}
static json quat(const btQuaternion&q){return json::array({q.x(),q.y(),q.z(),q.w()});}
static void require(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
struct Filter:btOverlapFilterCallback{
    std::vector<double>arc;double radius;
    bool needBroadphaseCollision(btBroadphaseProxy*a,btBroadphaseProxy*b)const override{
        bool masks=(a->m_collisionFilterGroup&b->m_collisionFilterMask)&&(b->m_collisionFilterGroup&a->m_collisionFilterMask);
        if(!masks)return false;
        auto*x=static_cast<btCollisionObject*>(a->m_clientObject);auto*y=static_cast<btCollisionObject*>(b->m_clientObject);
        if(x->getUserIndex2()!=0||y->getUserIndex2()!=0)return true;
        int i=x->getUserIndex(),j=y->getUserIndex();if(i>j)std::swap(i,j);
        if(j==i+1||arc[j]-arc[i+1]<SIMD_PI*radius)return false;
        bool knot=std::min(arc[i],arc.back()-arc[i+1])<4*radius&&std::min(arc[j],arc.back()-arc[j+1])<4*radius;
        return !knot;
    }
};
static json simulate(const json&source,const json&descriptor,bool defaultGroups){
    auto start=Clock::now();const double dt=1.0/240,damp=std::exp(-18*dt);
    require(source["ropes"].size()==1,"One-loop fixture only");
    const auto&rope=source["ropes"][0];auto lengths=rope["restLengths"].get<std::vector<double>>();
    int n=int(lengths.size());double rho=rope["linearMass"].get<double>(),radius=rope["radius"].get<double>();
    require(rope["supports"].size()==2&&point(rope["supports"]["0"])==point(rope["supports"][std::to_string(n)]),"Original common endpoint supports required");
    btDefaultCollisionConfiguration config;btCollisionDispatcher dispatcher(&config);
    btGImpactCollisionAlgorithm::registerAlgorithm(&dispatcher);
    btDbvtBroadphase broadphase;btMultiBodyConstraintSolver solver;
    btMultiBodyDynamicsWorld world(&dispatcher,&broadphase,&solver,&config);
    world.setGravity(btVector3(0,0,0));world.getSolverInfo().m_solverMode&=~SOLVER_USE_WARMSTARTING;
    require(world.getSolverInfo().m_numIterations==10,"Unexpected stock iteration default");
    Filter filter;filter.radius=radius;filter.arc.push_back(0);
    for(double l:lengths)filter.arc.push_back(filter.arc.back()+l);
    broadphase.getOverlappingPairCache()->setOverlapFilterCallback(&filter);
    btTriangleMesh triangles(true,false);
    for(auto&t:descriptor["collision"]["triangles"])triangles.addTriangle(point(descriptor["collision"]["vertices"][t[0].get<int>()]),point(descriptor["collision"]["vertices"][t[1].get<int>()]),point(descriptor["collision"]["vertices"][t[2].get<int>()]),false);
    btGImpactMeshShape mesh(&triangles);mesh.setMargin(0);mesh.updateBound();
    require(mesh.getMargin()==0,"Mesh margin mismatch");
    auto q=source["orientation"];btQuaternion old(q[0].get<double>(),q[1].get<double>(),q[2].get<double>(),q[3].get<double>());
    btQuaternion target(btVector3(0,0,1),SIMD_HALF_PI);
    double angle=2*std::acos(std::min(1.0,std::abs(old.dot(target))));
    btQuaternion next=old.slerp(target,std::min(1.0,dt*2.1/angle));
    // Use a real prismatic coordinate: the pinned rigid-body contact denominator
    // does not honor a constrained body's translational linearFactor.
    btMultiBody boardBody(1,0,btVector3(0,0,0),true,false);
    boardBody.setBasePos(btVector3(0,0,0));boardBody.setWorldToBaseRot(btQuaternion::getIdentity());
    boardBody.setupPrismatic(0,source["boardMass"].get<double>(),btVector3(1,1,1),-1,next.inverse(),quatRotate(next.inverse(),btVector3(0,1,0)),btVector3(0,0,0),btVector3(0,0,0),false);
    boardBody.finalizeMultiDof();boardBody.setLinearDamping(0);boardBody.setAngularDamping(0);
    boardBody.setJointPos(0,source["boardHeight"].get<double>());
    boardBody.setJointVel(0,(source["boardVerticalVelocity"].get<double>()-9.81*dt)*damp);
    btMultiBodyLinkCollider board(&boardBody,0);board.setCollisionShape(&mesh);
    board.setFriction(0);board.setRestitution(0);board.setUserIndex2(-1);boardBody.getLink(0).m_collider=&board;
    btAlignedObjectArray<btQuaternion>boardQ;btAlignedObjectArray<btVector3>boardP;
    boardBody.forwardKinematics(boardQ,boardP);boardBody.updateCollisionObjectWorldTransforms(boardQ,boardP);
    require((board.getWorldTransform().getOrigin()-btVector3(0,source["boardHeight"].get<double>(),0)).length()<1e-12,"Prismatic board transform mismatch");
    require(std::abs(board.getWorldTransform().getRotation().dot(next))>1-1e-12,"Prescribed board orientation mismatch");
    world.addMultiBody(&boardBody);if(defaultGroups)world.addCollisionObject(&board);else world.addCollisionObject(&board,btBroadphaseProxy::DefaultFilter,btBroadphaseProxy::AllFilter);
    btMultiBody body(n,0,btVector3(0,0,0),true,false);
    body.setBasePos(point(rope["supports"]["0"]));body.setWorldToBaseRot(btQuaternion::getIdentity());
    body.setHasSelfCollision(true);body.setLinearDamping(0);body.setAngularDamping(0);
    std::vector<btQuaternion>rotation;std::vector<btVector3>angular;
    double mass=0;
    for(int i=0;i<n;++i){
        btVector3 a=point(rope["positions"][i]),b=point(rope["positions"][i+1]);
        btVector3 dir=(b-a).normalized();btQuaternion rot=shortestArcQuat(btVector3(0,1,0),dir);rotation.push_back(rot);
        double m=rho*lengths[i],I=m*lengths[i]*lengths[i]/4;mass+=m;
        btQuaternion parent=i?rotation[i-1]:btQuaternion::getIdentity();
        body.setupSpherical(i,m,btVector3(I,I*1e-6,I),i-1,rot.inverse()*parent,
            i?btVector3(0,lengths[i-1]/2,0):btVector3(0,0,0),btVector3(0,lengths[i]/2,0),false);
        require(body.getLinkMass(i)==m&&body.getLinkInertia(i)==btVector3(I,I*1e-6,I),"Installed link properties mismatch");
        angular.push_back(dir.cross(point(rope["velocities"][i+1])-point(rope["velocities"][i]))/lengths[i]);
    }
    body.finalizeMultiDof();
    for(int i=0;i<n;++i){
        btVector3 relative=quatRotate(rotation[i].inverse(),angular[i]-(i?angular[i-1]:btVector3(0,0,0)));
        double joint[3]={relative.x(),relative.y(),relative.z()};body.setJointVelMultiDof(i,joint);
    }
    std::vector<std::unique_ptr<btCapsuleShape>>shapes;
    std::vector<std::unique_ptr<btMultiBodyLinkCollider>>colliders;
    btAlignedObjectArray<btQuaternion>scratchQ;btAlignedObjectArray<btVector3>scratchP;
    body.forwardKinematics(scratchQ,scratchP);
    for(int i=0;i<n;++i){
        shapes.push_back(std::make_unique<btCapsuleShape>(radius,lengths[i]));
        require(shapes.back()->getRadius()==radius&&shapes.back()->getMargin()==radius,"Capsule physical radius/margin mismatch");
        colliders.push_back(std::make_unique<btMultiBodyLinkCollider>(&body,i));
        auto&c=*colliders.back();c.setCollisionShape(shapes.back().get());c.setFriction(0);c.setRestitution(0);c.setUserIndex(i);c.setUserIndex2(0);
        c.setWorldTransform(body.getLink(i).m_cachedWorldTransform);
        body.getLink(i).m_collider=&c;if(defaultGroups)world.addCollisionObject(&c);else world.addCollisionObject(&c,btBroadphaseProxy::DefaultFilter,btBroadphaseProxy::AllFilter);
    }
    auto verifyProxy=[](const btCollisionObject& object){
        const auto* proxy=object.getBroadphaseHandle();
        require(proxy&&proxy->m_collisionFilterGroup==btBroadphaseProxy::DefaultFilter&&proxy->m_collisionFilterMask==btBroadphaseProxy::AllFilter,"Collider collision groups exclude required contacts");
    };
    verifyProxy(board);for(const auto& c:colliders)verifyProxy(*c);
    world.addMultiBody(&body);
    auto forward=[&](){body.forwardKinematics(scratchQ,scratchP);body.updateCollisionObjectWorldTransforms(scratchQ,scratchP);world.updateAabbs();};
    forward();
    auto endpoint=[&](int i,int sign){return body.localPosToWorld(i,btVector3(0,sign*lengths[i]/2,0));};
    double initialError=0,velocityError=0,closureInitial=(endpoint(n-1,1)-point(rope["supports"][std::to_string(n)])).length();
    std::vector<btVector3>omega(n+1),vel(n+1);body.compTreeLinkVelocities(omega.data(),vel.data());
    for(int i=0;i<n;++i){
        initialError=std::max(initialError,std::max((endpoint(i,-1)-point(rope["positions"][i])).length(),(endpoint(i,1)-point(rope["positions"][i+1])).length()));
        for(int sign:{-1,1}){
            btVector3 v=body.localDirToWorld(i,vel[i+1]+omega[i+1].cross(btVector3(0,sign*lengths[i]/2,0)));
            require(std::isfinite(v.x())&&std::isfinite(v.y())&&std::isfinite(v.z()),"Nonfinite velocity projection");
            velocityError=std::max(velocityError,(v-point(rope["velocities"][i+(sign>0?1:0)])).length());
        }
    }
    require(std::isfinite(velocityError)&&initialError<=1e-8&&closureInitial<=1e-8,"Initial articulated endpoint import failed");
    btMultiBodyPoint2Point closure(&body,n-1,static_cast<btRigidBody*>(nullptr),btVector3(0,lengths.back()/2,0),point(rope["supports"][std::to_string(n)]));
    world.addMultiBodyConstraint(&closure);
    for(int i=0;i<n;++i){
        const auto*v=body.getJointVelMultiDof(i);double damped[3]={v[0]*damp,v[1]*damp,v[2]*damp};body.setJointVelMultiDof(i,damped);
        body.addLinkForce(i,btVector3(0,-9.81*damp*body.getLinkMass(i),0));
    }
    double setup=seconds(start);auto t=Clock::now();world.stepSimulation(dt,0);double update=seconds(t);forward();
    json checkpoint=source;checkpoint["boardHeight"]=board.getWorldTransform().getOrigin().y();checkpoint["boardVerticalVelocity"]=boardBody.getJointVel(0);checkpoint["orientation"]=quat(board.getWorldTransform().getRotation());
    json capsules=json::array(),positions=json::array(),velocities=json::array(),engineState=json::array();
    double internalGap=0,closureGap=(endpoint(n-1,1)-point(rope["supports"][std::to_string(n)])).length();
    body.compTreeLinkVelocities(omega.data(),vel.data());
    for(int i=0;i<n;++i){
        if(i)internalGap=std::max(internalGap,(endpoint(i-1,1)-endpoint(i,-1)).length());
        capsules.push_back({{"a",arr(endpoint(i,-1))},{"b",arr(endpoint(i,1))}});
        auto tr=colliders[i]->getWorldTransform();engineState.push_back({{"position",arr(tr.getOrigin())},{"rotation",quat(tr.getRotation())},{"localVelocity",arr(vel[i+1])},{"localAngularVelocity",arr(omega[i+1])}});
    }
    for(int i=0;i<=n;++i){
        btVector3 p=i==n?endpoint(n-1,1):endpoint(i,-1);
        require(std::isfinite(p.x())&&std::isfinite(p.y())&&std::isfinite(p.z()),"Nonfinite stock state");
        if(rope["supports"].contains(std::to_string(i)))p=point(rope["supports"][std::to_string(i)]);
        positions.push_back(arr(p));velocities.push_back(arr((p-point(rope["positions"][i]))/dt));
    }
    checkpoint["ropes"][0]["previousPositions"]=rope["positions"];checkpoint["ropes"][0]["positions"]=positions;checkpoint["ropes"][0]["velocities"]=velocities;
    int woodManifolds=0,woodPoints=0,positiveWood=0,selfManifolds=0,selfPoints=0,emptySelfManifolds=0;
    double totalWoodImpulse=0;
    for(int i=0;i<dispatcher.getNumManifolds();++i){
        auto*m=dispatcher.getManifoldByIndexInternal(i);bool wood=m->getBody0()==&board||m->getBody1()==&board;
        if(wood){++woodManifolds;woodPoints+=m->getNumContacts();for(int j=0;j<m->getNumContacts();++j){double impulse=m->getContactPoint(j).getAppliedImpulse();if(impulse>0){++positiveWood;totalWoodImpulse+=impulse;}}}else{++selfManifolds;selfPoints+=m->getNumContacts();if(!m->getNumContacts())++emptySelfManifolds;}
    }
    json report={{"checkpoint",checkpoint},{"actualCapsules",json::array({{{"id",rope["id"]},{"capsules",capsules}}})},{"engineState",engineState},
        {"initialEndpointError",initialError},{"initialVelocityProjectionError",velocityError},{"totalRopeMass",mass},{"internalEndpointGap",internalGap},{"supportClosureGap",closureGap},
        {"setupSeconds",setup},{"updateSeconds",update},{"woodContactManifolds",woodManifolds},{"woodContactPoints",woodPoints},{"positiveWoodImpulsePoints",positiveWood},{"totalWoodImpulse",totalWoodImpulse},{"selfManifolds",selfManifolds},{"selfContactPoints",selfPoints},{"emptySelfManifolds",emptySelfManifolds},{"broadphasePairs",broadphase.getOverlappingPairCache()->getNumOverlappingPairs()},
        {"solverIterations",world.getSolverInfo().m_numIterations},{"closureImpulse",{closure.getAppliedImpulse(0),closure.getAppliedImpulse(1),closure.getAppliedImpulse(2)}}};
    world.removeMultiBodyConstraint(&closure);world.removeMultiBody(&body);
    for(auto&c:colliders)world.removeCollisionObject(c.get());world.removeCollisionObject(&board);world.removeMultiBody(&boardBody);
    return report;
}
int run(int argc,char**argv){
    if(argc!=4&&argc!=5)return 2;bool defaultGroups=argc==5&&std::string(argv[4])=="--default-groups";json checkpoint,descriptor;std::ifstream(argv[1])>>checkpoint;std::ifstream(argv[2])>>descriptor;
    json reports=json::array();for(int i=0;i<2;++i)reports.push_back(simulate(checkpoint,descriptor,defaultGroups));
    std::ofstream(argv[3])<<reports.dump(2)<<"\n";
    for(auto&r:reports)std::cout<<"update "<<r["updateSeconds"]<<" internal gap "<<r["internalEndpointGap"]<<" closure gap "<<r["supportClosureGap"]<<"\n";
    return 0;
}

int main(int argc,char**argv){try{return run(argc,argv);}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 3;}}
