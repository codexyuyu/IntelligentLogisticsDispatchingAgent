// Optional Neo4j input projection; not executed or required by current architecture.
// Copy graph CSV files to the configured Neo4j import directory.
CREATE CONSTRAINT prep_node_id IF NOT EXISTS FOR (n:PreparationNode) REQUIRE n.id IS UNIQUE;
LOAD CSV WITH HEADERS FROM "file:///graph_nodes.csv" AS row MERGE (n:PreparationNode {id: row.id}) SET n.scenario=row.scenario,n.kind=row.kind,n.code=row.code,n.source="synthetic";
LOAD CSV WITH HEADERS FROM "file:///graph_edges.csv" AS row MATCH (a:PreparationNode {id:row.source_id}), (b:PreparationNode {id:row.target_id}) MERGE (a)-[r:INPUT_RELATION {kind:row.relation}]->(b);
