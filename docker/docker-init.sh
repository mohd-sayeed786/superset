#!/usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
set -e

#
# Always install local overrides first
#
/app/docker/docker-bootstrap.sh

if [ "$SUPERSET_LOAD_EXAMPLES" = "yes" ]; then
    STEP_CNT=4
else
    STEP_CNT=3
fi

echo_step() {
cat <<EOF
######################################################################
Init Step ${1}/${STEP_CNT} [${2}] -- ${3}
######################################################################
EOF
}
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
# If Cypress run – overwrite the password for admin and export env variables
if [ "$CYPRESS_CONFIG" == "true" ]; then
    ADMIN_PASSWORD="general"
    export SUPERSET_TESTENV=true
    export POSTGRES_DB=superset_cypress
    export SUPERSET__SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://superset:superset@db:5432/superset_cypress
fi
# Initialize the database
echo_step "1" "Starting" "Applying DB migrations"
superset db upgrade
echo_step "1" "Complete" "Applying DB migrations"

# Create an admin user
echo_step "2" "Starting" "Setting up admin user ( admin / $ADMIN_PASSWORD )"
if [ "$CYPRESS_CONFIG" == "true" ]; then
    superset load_test_users
else
    superset fab create-admin \
        --username admin \
        --email admin@superset.com \
        --password "$ADMIN_PASSWORD" \
        --firstname Superset \
        --lastname Admin
fi
echo_step "2" "Complete" "Setting up admin user"
# Create default roles and permissions
echo_step "3" "Starting" "Setting up roles and perms"
superset init
echo_step "3" "Complete" "Setting up roles and perms"

if [ "$SUPERSET_LOAD_EXAMPLES" = "yes" ]; then
    # Load some data to play with
    echo_step "4" "Starting" "Loading examples"


    # If Cypress run which consumes superset_test_config – load required data for tests
    if [ "$CYPRESS_CONFIG" == "true" ]; then
        superset load_examples --load-test-data
    else
        # Load a curated subset of examples for faster startup.
        # Set SUPERSET_LOAD_ALL_EXAMPLES=yes to load everything instead.
        if [ "$SUPERSET_LOAD_ALL_EXAMPLES" = "yes" ]; then
            superset load_examples
        else
            python -c "
from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.examples.data_loading import (
        load_css_templates,
        load_examples_from_configs,
        discover_datasets,
    )
    import superset.utils.database as database_utils
    database_utils.get_example_database()
    load_css_templates()

    # Load only these example datasets
    SELECTED = [
        'load_world_health',
        'load_sales_dashboard',
        'load_usa_births_names',
        'load_international_sales',
    ]
    loaders = discover_datasets()
    for name in SELECTED:
        if name in loaders:
            print(f'Loading {name}...')
            try:
                loaders[name]()
            except Exception as e:
                print(f'Warning: {name} failed: {e}')

    # Load YAML-config-based examples (charts/dashboards)
    load_examples_from_configs(False, False)
    print('Selected examples loaded successfully.')
"
        fi
    fi
    echo_step "4" "Complete" "Loading examples"
fi
