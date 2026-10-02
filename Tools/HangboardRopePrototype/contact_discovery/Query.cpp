// Proposal-only triangle discovery. No normals, constraints or dynamics reused.
#include <Jolt/Jolt.h>
#include <Jolt/RegisterTypes.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Physics/Collision/CollisionDispatch.h>
#include <Jolt/Physics/Collision/CollisionCollectorImpl.h>
#include <Jolt/Physics/Collision/CollideShape.h>
#include <Jolt/Physics/Collision/Shape/MeshShape.h>
#include <Jolt/Physics/Collision/Shape/CapsuleShape.h>
#include <Jolt/Physics/Collision/Shape/SphereShape.h>
#include "json.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <stdexcept>
using namespace JPH;using json=nlohmann::json;
static Vec3 p(const json&j){return Vec3(j[0].get<float>(),j[1].get<float>(),j[2].get<float>());}
int main(int argc,char**argv){
 if(argc!=4)return 2;RegisterDefaultAllocator();Factory::sInstance=new Factory;RegisterTypes();
 json input,descriptor;std::ifstream(argv[1])>>input;std::ifstream(argv[2])>>descriptor;
 auto begin=std::chrono::steady_clock::now();VertexList vertices;IndexedTriangleList triangles;
 for(auto&v:descriptor["collision"]["vertices"]){auto x=p(v);vertices.emplace_back(x.GetX(),x.GetY(),x.GetZ());}
 uint id=0;for(auto&t:descriptor["collision"]["triangles"])triangles.emplace_back(t[0].get<uint>(),t[1].get<uint>(),t[2].get<uint>(),0,++id);
 MeshShapeSettings settings(vertices,triangles);settings.mPerTriangleUserData=true;
 auto result=settings.Create();if(result.HasError())throw std::runtime_error(result.GetError().c_str());
 auto* mesh=static_cast<const MeshShape*>(result.Get().GetPtr());
 double setup=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
 json queries=json::array();double total=0;
 for(auto&q:input["queries"]){
  auto start=std::chrono::steady_clock::now();Vec3 a=p(q["a"]),b=p(q["b"]),delta=b-a;
  RefConst<Shape>shape;Mat44 transform;
  if(q["a"]==q["b"]){shape=new SphereShape(q["radius"].get<float>());transform=Mat44::sTranslation(a);}
  else{shape=new CapsuleShape(delta.Length()/2,q["radius"].get<float>());transform=Mat44::sRotationTranslation(Quat::sFromTo(Vec3::sAxisY(),delta.Normalized()),(a+b)*.5f);}
  CollideShapeSettings collision;collision.mActiveEdgeMode=EActiveEdgeMode::CollideWithAll;collision.mBackFaceMode=EBackFaceMode::CollideWithBackFaces;collision.mMaxSeparationDistance=1e-6f;
  AllHitCollisionCollector<CollideShapeCollector>collector;
  CollisionDispatch::sCollideShapeVsShape(shape,mesh,Vec3::sReplicate(1),Vec3::sReplicate(1),transform,Mat44::sTranslation(mesh->GetCenterOfMass()),SubShapeIDCreator(),SubShapeIDCreator(),collision,collector);
  std::vector<uint>ids;for(auto&hit:collector.mHits){uint id=mesh->GetTriangleUserData(hit.mSubShapeID2);if(!id||id>triangles.size())throw std::runtime_error("Missing triangle provenance");ids.push_back(id-1);}
  std::sort(ids.begin(),ids.end());ids.erase(std::unique(ids.begin(),ids.end()),ids.end());
  total+=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  queries.push_back({{"triangles",ids},{"rawHits",collector.mHits.size()}});
 }
 std::ofstream(argv[3])<<json({{"queries",queries},{"setupSeconds",setup},{"querySeconds",total},{"discoveryPadding",1e-6},{"dynamicsSteps",0}}).dump(2)<<"\n";
 std::cout<<"query seconds "<<total<<" setup "<<setup<<"\n";
}
