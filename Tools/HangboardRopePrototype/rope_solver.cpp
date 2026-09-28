// Offline Bullet probe. The USDZ and package metadata remain unmodified.
#include "json-v3.12.0.hpp"

#include <BulletCollision/CollisionShapes/btConvexHullShape.h>
#include <BulletDynamics/ConstraintSolver/btSequentialImpulseConstraintSolver.h>
#include <BulletSoftBody/btSoftBody.h>
#include <BulletSoftBody/btSoftBodyRigidBodyCollisionConfiguration.h>
#include <BulletSoftBody/btSoftRigidDynamicsWorld.h>
#include <BulletCollision/BroadphaseCollision/btDbvtBroadphase.h>
#include <BulletCollision/CollisionDispatch/btCollisionDispatcher.h>
#include <LinearMath/btDefaultMotionState.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using json = nlohmann::json;

static btVector3 vec3(const json& values) {
  if (!values.is_array() || values.size() != 3) throw std::runtime_error("invalid vec3");
  btVector3 value(values.at(0).get<double>(), values.at(1).get<double>(), values.at(2).get<double>());
  if (!std::isfinite(value.x()) || !std::isfinite(value.y()) || !std::isfinite(value.z()))
    throw std::runtime_error("nonfinite vec3");
  return value;
}

static json array3(const btVector3& value) { return {value.x(), value.y(), value.z()}; }

struct Options {
  std::string case_path;
  std::string pose;
  std::string length_mode;
  std::string output;
};

static Options parse_args(int argc, char** argv) {
  Options options;
  for (int i = 1; i < argc; i += 2) {
    if (i + 1 >= argc) throw std::runtime_error("missing CLI value");
    const std::string key = argv[i];
    const std::string value = argv[i + 1];
    if (key == "--case") options.case_path = value;
    else if (key == "--pose") options.pose = value;
    else if (key == "--length-mode") options.length_mode = value;
    else if (key == "--output") options.output = value;
    else throw std::runtime_error("unknown CLI option: " + key);
  }
  if (options.case_path.empty() || options.pose.empty() || options.output.empty() ||
      (options.length_mode != "taut" && options.length_mode != "original"))
    throw std::runtime_error("required: --case --pose --length-mode original|taut --output");
  return options;
}

struct World {
  btSoftBodyRigidBodyCollisionConfiguration config;
  btCollisionDispatcher dispatcher{&config};
  btDbvtBroadphase broadphase;
  btSequentialImpulseConstraintSolver impulse_solver;
  btSoftRigidDynamicsWorld dynamics{&dispatcher, &broadphase, &impulse_solver, &config};
  btSoftBodyWorldInfo info;

  World() {
    dynamics.setGravity(btVector3(0, -9.81, 0));
    info.m_broadphase = &broadphase;
    info.m_dispatcher = &dispatcher;
    info.m_gravity = dynamics.getGravity();
    info.m_sparsesdf.Initialize();
    // Bullet defaults to 250 mm SDF voxels, larger than the entire bar section.
    info.m_sparsesdf.setDefaultVoxelsz(0.001);
    info.m_sparsesdf.Reset();
  }
};

struct Seed { std::vector<btVector3> points; size_t first_guide; size_t second_guide; };

static Seed seed_loop(const json& loop, const btVector3& anchor,
                                        const btVector3& local_anchor,
                                        const btVector3& local_center,
                                        const btQuaternion& rotation,
                                        const btVector3& translation,
                                        btScalar radial_extent, btScalar margin) {
  const btScalar dy = local_anchor.y() - local_center.y();
  const btScalar dz = local_anchor.z() - local_center.z();
  const btScalar direction_length = std::hypot(dy, dz);
  if (direction_length < 1e-5) throw std::runtime_error("anchor lies in body section");
  const btScalar uy = dy / direction_length, uz = dz / direction_length;
  const btScalar vy = -uz, vz = uy;
  constexpr int arc_segments = 40;
  std::vector<btVector3> points;
  points.reserve(arc_segments + 120);
  std::vector<btVector3> arc;
  arc.reserve(arc_segments + 1);
  for (int i = 0; i <= arc_segments; ++i) {
    const btScalar fraction = btScalar(i) / arc_segments;
    const btScalar theta = SIMD_PI * (btScalar(0.5) + fraction);
    const btScalar radial = radial_extent + margin;
    const btScalar local_x = loop.at("outer_x").get<double>() * (1 - fraction) +
                              loop.at("inner_x").get<double>() * fraction;
    const btVector3 local(local_x,
      local_center.y() + radial * (uy * std::cos(theta) + vy * std::sin(theta)),
      local_center.z() + radial * (uz * std::cos(theta) + vz * std::sin(theta)));
    arc.push_back(quatRotate(rotation, local) + translation);
  }
  constexpr btScalar max_link_length = 0.003;
  const auto append_span = [&](const btVector3& from, const btVector3& to) {
    const int segments = std::max(1, static_cast<int>(std::ceil((to - from).length() / max_link_length)));
    for (int i = 0; i < segments; ++i)
      points.push_back(from.lerp(to, btScalar(i) / segments));
  };
  append_span(anchor, arc.front());
  const size_t first_guide = points.size();
  for (size_t i = 0; i + 1 < arc.size(); ++i) append_span(arc[i], arc[i + 1]);
  const size_t second_guide = points.size();
  append_span(arc.back(), anchor);
  points.push_back(anchor);
  return {points, first_guide, second_guide};
}

static btScalar path_length(const std::vector<btVector3>& points) {
  btScalar result = 0;
  for (size_t i = 1; i < points.size(); ++i) result += (points[i] - points[i - 1]).length();
  return result;
}

static json solve(const json& input, const Options& options) {
  if (input.at("schemaVersion") != 1) throw std::runtime_error("unsupported case schema");
  const auto& pose = input.at("poses").at(options.pose);
  const auto& rotation_values = pose.at("rotation");
  if (!rotation_values.is_array() || rotation_values.size() != 4)
    throw std::runtime_error("invalid pose rotation");
  btQuaternion rotation(rotation_values.at(0).get<double>(), rotation_values.at(1).get<double>(),
                        rotation_values.at(2).get<double>(), rotation_values.at(3).get<double>());
  if (std::abs(rotation.length() - 1) > 1e-4) throw std::runtime_error("invalid unit quaternion");
  rotation.normalize();
  const btVector3 translation = vec3(pose.at("translation"));
  const btVector3 anchor = vec3(input.at("anchor"));
  const btVector3 local_anchor = quatRotate(rotation.inverse(), anchor - translation);

  const auto& source_vertices = input.at("vertices");
  const auto& source_faces = input.at("faces");
  if (source_vertices.size() < 4 || source_faces.size() < 4)
    throw std::runtime_error("body mesh is empty");
  std::vector<btVector3> local_vertices;
  local_vertices.reserve(source_vertices.size());
  btVector3 minimum(BT_LARGE_FLOAT, BT_LARGE_FLOAT, BT_LARGE_FLOAT);
  btVector3 maximum(-BT_LARGE_FLOAT, -BT_LARGE_FLOAT, -BT_LARGE_FLOAT);
  for (const auto& values : source_vertices) {
    const btVector3 p = vec3(values);
    local_vertices.push_back(p);
    minimum.setMin(p);
    maximum.setMax(p);
  }
  const btVector3 local_center = (minimum + maximum) / 2;
  const btScalar radial_extent = std::max((maximum.y() - minimum.y()) / 2,
                                           (maximum.z() - minimum.z()) / 2);
  if (radial_extent <= 0) throw std::runtime_error("body section is degenerate");

  World world;
  for (const auto& face : source_faces) {
    if (!face.is_array() || face.size() != 3) throw std::runtime_error("nontriangle body face");
    const auto a = face.at(0).get<size_t>(), b = face.at(1).get<size_t>(), c = face.at(2).get<size_t>();
    if (a >= local_vertices.size() || b >= local_vertices.size() || c >= local_vertices.size())
      throw std::runtime_error("body face index outside vertex array");
  }
  btConvexHullShape body_shape;
  for (const btVector3& vertex : local_vertices)
    body_shape.addPoint(quatRotate(rotation, vertex) + translation, false);
  body_shape.recalcLocalAabb();
  body_shape.setMargin(0);
  btDefaultMotionState body_motion(btTransform::getIdentity());
  btRigidBody::btRigidBodyConstructionInfo body_info(0, &body_motion, &body_shape);
  btRigidBody body(body_info);
  world.dynamics.addRigidBody(&body);

  const auto& input_loops = input.at("loops");
  if (input_loops.size() != 2) throw std::runtime_error("expected two loops");
  std::vector<btSoftBody*> ropes;
  std::vector<std::string> loop_ids;
  std::vector<btScalar> target_lengths;
  json result_loops = json::object();
  constexpr btScalar collision_margin = 0.00025;
  for (const auto& loop : input_loops) {
    if (loop.at("wrap_side") != "opposite-anchor")
      return {{"status", "invalid_topology"}, {"reason", "unsupported wrap side"}};
    const btScalar radius = loop.at("radius").get<double>();
    const btScalar rest_length = loop.at("rest_length").get<double>();
    if (radius <= 0 || rest_length <= 0) throw std::runtime_error("invalid rope radius or length");
    const auto seed = seed_loop(loop, anchor, local_anchor, local_center, rotation, translation,
                                radial_extent, radius + 0.001);
    const auto taut_seed = seed_loop(loop, anchor, local_anchor, local_center, rotation, translation,
                                     radial_extent, radius);
    const btScalar initial_length = path_length(seed.points);
    const btScalar target_length = options.length_mode == "taut" ? path_length(taut_seed.points) : rest_length;
    std::vector<btScalar> masses(seed.points.size(), 0.002);
    masses.front() = masses.back() = 0;
    // The two declared passage positions are fixed guides; only the intervening
    // contact route is free to settle against the collider.
    masses[seed.first_guide] = masses[seed.second_guide] = 0;
    auto* rope = new btSoftBody(&world.info, static_cast<int>(seed.points.size()), seed.points.data(), masses.data());
    for (size_t i = 0; i + 1 < seed.points.size(); ++i) rope->appendLink(static_cast<int>(i), static_cast<int>(i + 1));
    rope->updateLinkConstants();
    rope->m_bUpdateRtCst = false; // A deferred updateConstants would reset the selected rest length.
    rope->setRestLengthScale(target_length / initial_length);
    rope->m_cfg.piterations = 30;
    rope->m_cfg.kDP = 0.08;
    rope->m_cfg.kDF = 0.5;
    rope->m_materials[0]->m_kLST = 1;
    rope->m_cfg.collisions = btSoftBody::fCollision::SDF_RS;
    rope->getCollisionShape()->setMargin(radius + collision_margin);
    world.dynamics.addSoftBody(rope);
    ropes.push_back(rope);
    loop_ids.push_back(loop.at("id").get<std::string>());
    target_lengths.push_back(target_length);
  }

  constexpr int max_steps = 3000;
  constexpr btScalar step_size = btScalar(1) / 240;
  btScalar residual = std::numeric_limits<btScalar>::infinity();
  int completed_steps = 0;
  std::vector<btVector3> previous;
  for (int step = 0; step < max_steps; ++step) {
    if (step % 120 == 0) {
      previous.clear();
      for (auto* rope : ropes) for (int j = 0; j < rope->m_nodes.size(); ++j)
        previous.push_back(rope->m_nodes[j].m_x);
    }
    world.dynamics.stepSimulation(step_size, 1, step_size);
    completed_steps = step + 1;
    if (step % 120 == 119) {
      residual = 0;
      size_t index = 0;
      for (auto* rope : ropes) for (int j = 0; j < rope->m_nodes.size(); ++j)
        residual = std::max(residual, (rope->m_nodes[j].m_x - previous[index++]).length());
      if (completed_steps >= 480 && residual < 2e-5) break;
    }
  }
  for (size_t i = 0; i < ropes.size(); ++i) {
    json centerline = json::array();
    for (int j = 0; j < ropes[i]->m_nodes.size(); ++j)
      centerline.push_back(array3(ropes[i]->m_nodes[j].m_x));
    result_loops[loop_ids[i]] = {{"centerline", centerline}, {"targetLength", target_lengths[i]}};
  }
  json result = {
    {"status", residual < 2e-5 ? "settled" : "nonconverged"},
    {"steps", completed_steps}, {"iterations", 30},
    {"convergenceResidual", residual}, {"collisionMargin", collision_margin},
    {"lengthMode", options.length_mode}, {"loops", result_loops}
  };
  for (auto* rope : ropes) world.dynamics.removeSoftBody(rope);
  for (auto* rope : ropes) delete rope;
  world.dynamics.removeRigidBody(&body);
  return result;
}

int main(int argc, char** argv) {
  std::string output;
  try {
    const Options options = parse_args(argc, argv);
    output = options.output;
    std::ifstream in(options.case_path);
    if (!in) throw std::runtime_error("cannot open case");
    json input;
    in >> input;
    const json result = solve(input, options);
    std::ofstream out(output);
    out << result.dump(2) << '\n';
    return result.at("status") == "settled" ? 0 : 2;
  } catch (const std::exception& error) {
    if (!output.empty()) {
      std::ofstream out(output);
      out << json({{"status", "error"}, {"reason", error.what()}}).dump(2) << '\n';
    }
    std::cerr << error.what() << '\n';
    return 2;
  }
}
