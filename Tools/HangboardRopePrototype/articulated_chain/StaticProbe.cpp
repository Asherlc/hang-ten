#include <btBulletCollisionCommon.h>
#include <BulletCollision/Gimpact/btGImpactShape.h>
#include <BulletCollision/Gimpact/btGImpactCollisionAlgorithm.h>
#include "json.hpp"
#include <memory>
#include <fstream>
#include <iostream>
using json=nlohmann::json;
static btVector3 p(const json&j){return btVector3(j[0].get<double>(),j[1].get<double>(),j[2].get<double>());}
static btQuaternion q(const json&j){return btQuaternion(j[0].get<double>(),j[1].get<double>(),j[2].get<double>(),j[3].get<double>());}
static json query(const json&source,const json&descriptor,const json&result,bool final){
    btDefaultCollisionConfiguration config;btCollisionDispatcher dispatcher(&config);
    btGImpactCollisionAlgorithm::registerAlgorithm(&dispatcher);btDbvtBroadphase broad;
    btCollisionWorld world(&dispatcher,&broad,&config);
    btTriangleMesh triangles(true,false);
    for(auto&t:descriptor["collision"]["triangles"])triangles.addTriangle(p(descriptor["collision"]["vertices"][t[0].get<int>()]),p(descriptor["collision"]["vertices"][t[1].get<int>()]),p(descriptor["collision"]["vertices"][t[2].get<int>()]),false);
    btGImpactMeshShape mesh(&triangles);mesh.setMargin(0);mesh.updateBound();
    btCollisionObject board;board.setCollisionFlags(0);board.setCollisionShape(&mesh);
    board.setWorldTransform(btTransform(q(result["checkpoint"]["orientation"]),btVector3(0,(final?result["checkpoint"]:source)["boardHeight"].get<double>(),0)));
    world.addCollisionObject(&board,1,2);
    const auto&rope=source["ropes"][0];int n=int(rope["restLengths"].size());
    std::vector<std::unique_ptr<btCapsuleShape>>shapes;std::vector<std::unique_ptr<btCollisionObject>>capsules;
    for(int i=0;i<n;++i){
        btVector3 a=final?p(result["actualCapsules"][0]["capsules"][i]["a"]):p(rope["positions"][i]);
        btVector3 b=final?p(result["actualCapsules"][0]["capsules"][i]["b"]):p(rope["positions"][i+1]);
        shapes.push_back(std::make_unique<btCapsuleShape>(rope["radius"].get<double>(),rope["restLengths"][i].get<double>()));
        capsules.push_back(std::make_unique<btCollisionObject>());auto&c=*capsules.back();c.setCollisionFlags(0);
        c.setCollisionShape(shapes.back().get());c.setWorldTransform(btTransform(shortestArcQuat(btVector3(0,1,0),(b-a).normalized()),(a+b)*.5));
        c.setUserIndex(i);world.addCollisionObject(&c,2,1);
    }
    world.performDiscreteCollisionDetection();
    json points=json::array();int manifolds=0;
    for(int i=0;i<dispatcher.getNumManifolds();++i){
        auto*m=dispatcher.getManifoldByIndexInternal(i);if(m->getBody0()!=&board&&m->getBody1()!=&board)continue;
        ++manifolds;const auto*other=m->getBody0()==&board?m->getBody1():m->getBody0();
        for(int j=0;j<m->getNumContacts();++j)points.push_back({{"link",other->getUserIndex()},{"distance",m->getContactPoint(j).getDistance()}});
    }
    for(auto&c:capsules)world.removeCollisionObject(c.get());world.removeCollisionObject(&board);
    return {{"pose",final?"retained-final":"initial-after-prescribed-rotation"},{"manifolds",manifolds},{"points",points},{"dynamicsSteps",0}};
}
int main(int argc,char**argv){
    if(argc!=5)return 2;json source,descriptor,result;
    std::ifstream(argv[1])>>source;std::ifstream(argv[2])>>descriptor;std::ifstream(argv[3])>>result;
    json output=json::array({query(source,descriptor,result[0],false),query(source,descriptor,result[0],true)});
    std::ofstream(argv[4])<<output.dump(2)<<"\n";
    for(auto&x:output)std::cout<<x["pose"]<<" manifolds "<<x["manifolds"]<<" points "<<x["points"].size()<<"\n";
}
