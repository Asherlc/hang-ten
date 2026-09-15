#!/usr/bin/env ruby
# Runs the exact checked-out solver and BoardModelView clearance gate on macOS,
# including every triangle from the real hash-checked package USDZs.
# No Xcode app build or third-party dependency is needed.
require "open3"
require "tmpdir"
require "fileutils"

Dir.chdir(File.expand_path("../..", __dir__))
owner = File.basename(ENV.fetch("PASEO_WORKTREE_PATH", Dir.pwd))
FileUtils.mkdir_p(".context")
models = File.read("HangTen/Models/TrainingModels.swift")
view = File.read("HangTen/Views/BoardModelView.swift")
types = models[/struct BoardModelBounds:.*?(?=struct BoardModelFacePlaneAABB)/m] +
        models[/struct BoardModelAttachment:.*?(?=struct BoardModelContactDescriptor)/m]
source = "import Foundation\nimport SceneKit\nimport simd\n" + types +
         File.read("HangTen/Models/SuspensionProfiles.swift").split("private extension SIMD3").first +
         File.read("HangTen/Views/SuspendedBoardPresentation.swift") +
         view[/enum BoardModelSolvedSuspension.*?(?=enum BoardModelAsset)/m]
source += "\nclass ProductionClearanceCheck {\nvar boardContainer = SCNNode()\nvar suspension: BoardModelSuspension?\nvar geometryByNodeID: [String: SCNNode] = [:]\n"
gate = view[/    private func hasClearance.*?(?=    private func nodeID\(for node:)/m]
abort("Could not locate production clearance gate") unless gate
if ARGV.include?("--diagnose")
  gate = gate.sub("                    return false\n                }\n                }", '                    print("COLLISION", nodeID, pathIndex, segmentIndex, "local", simd_inverse(solved.boardTransform) * SIMD4(points.0, 1), simd_inverse(solved.boardTransform) * SIMD4(points.1, 1), "distance", sqrt(approach.distanceSquared), "required", requiredDistance)' + "\n                    return false\n                }\n                }")
end
source += gate.sub("private func hasClearance", "func hasClearance")
source += "\n}\n" + File.read("Tools/HangboardModels/production_cord_clearance.swift")
Dir.mktmpdir("#{owner}-production-cord-clearance-", ".context") do |cache|
  Open3.popen3("swift", "-module-cache-path", cache, "-") do |input, output, error, wait|
    input.write(source)
    input.close
    reader = Thread.new { warn error.read }
    puts output.read
    reader.join
    abort("Production cord clearance regression failed") unless wait.value.success?
  end
end
