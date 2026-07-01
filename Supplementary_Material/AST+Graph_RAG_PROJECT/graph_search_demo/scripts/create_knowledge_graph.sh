python src/cli.py \
  --create_kg \
  --ast_data_path "./examples/code/ast_result_all_bundle_version20240914.json" \
  --graph_save_path "./examples/code/code_graph_all_bundle_version20240914.json" \
  --community_map_save_path "./examples/code/community_map_all_bundle_version20240914.json" \
  --community_reports_save_path "./examples/code/community_reports_all_bundle_version20240914.json" \
  --edge_power_graph_save_path "./examples/code/edge_power_graph_all_bundle_version20240914.json" \
  --max_cluster_size 50 \
  --concurrent_num 5 \