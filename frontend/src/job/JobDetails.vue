<template>
    <div>
        <b-button @click="gotoJobsView">View All Jobs</b-button>
        <div class="container">
            <div v-if="job.parent_job_id">
                <b-button @click="goToSingleView(job.parent_job_id)">Go to Parent Job</b-button>
            </div>
            <b-field label="ID">
                <p>{{job.job_id}}</p>
            </b-field>
            <b-field label="Name">
                <p>{{job.name}}</p>
            </b-field>
            <b-field label="Type">
                <p>{{job.job_type}}</p>
            </b-field>
            <b-field label="Status">
                <p>{{job.state}}</p>
            </b-field>
            <b-field label="User" v-if="job.user">
                <p>{{job.user}}</p>
            </b-field>
            <b-field label="Created">
                <p>{{job.created}}</p>
            </b-field>
            <b-field label="Last Updated">
                <p>{{job.updated}}</p>
            </b-field>
            <b-field label="Duration">
                <p>{{job.duration}}</p>
            </b-field>
            <b-field label="Children" v-if="job.children && job.children.length > 0">
                <b-table :data="job.children"
                         default-sort="created" :default-sort-direction="'asc'">
                    <template slot-scope="props">
                        <b-table-column field="type" label="Type">
                            {{ props.row.type}}
                        </b-table-column>
                        <b-table-column field="state" label="Status">
                            {{ props.row.state}}
                        </b-table-column>
                        <b-table-column field="job_id" label="ID">
                            {{ props.row.job_id}}
                        </b-table-column>
                        <b-table-column field="job_id" label="">
                            <b-button @click="goToSingleView(props.row.job_id)">
                                Single View
                            </b-button>
                        </b-table-column>
                    </template>
                </b-table>
            </b-field>
            <b-message v-if="job.errors && job.errors.length > 0"
                       title="Errors" type="is-danger" has-icon :closable="false">
                <b-table :data="job.errors">
                    <template slot-scope="props">
                        <b-table-column field="job_name" label="Failed task name">
                            {{props.row.job_name}}
                        </b-table-column>
                        <b-table-column field="job_id" label="Failed task ID">
                            {{props.row.job_id}}
                        </b-table-column>
                    <b-table-column field="message" label="Error">
                        {{ props.row.message}}
                    </b-table-column>
                    <b-table-column field="job_id" label="">
                        <b-button @click="goToSingleView(props.row.job_id)">Show Task</b-button>
                    </b-table-column>
                    </template>
                </b-table>
            </b-message>
            <b-collapse :open="false" aria-id="job-params">
                <button class="button" slot="trigger" aria-controls="job-params">
                    Show Job Parameters
                </button>
                <pre>{{ job.parameters }}</pre>
            </b-collapse>
        </div>
    </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BField from 'buefy/src/components/field/Field.vue';
import { getJobDetails, Job } from './JobClient';
import { showError } from '@/util/Notifier.ts';

@Component({
    components: { BField }
})
export default class JobDetails extends Vue {
    jobID: string = '';
    job: Job = {} as any;

    mounted() {
        this.jobID = this.$route.query.id as string;
        this.loadJobDetails();
    }

    goToSingleView(id: string) {
        this.$router.push({
            query: { id }
        });
        this.jobID = id;
        this.loadJobDetails();
    }

    gotoJobsView() {
        this.$router.push({ path: 'jobs' });
    }

    async loadJobDetails() {
        try {
            this.job = await getJobDetails(this.jobID);
        } catch (e) {
            showError('Failed to retrieve job details from server!', e);
        }
    }
}
</script>

<style lang="scss">
.container {
    text-align: left;
}
</style>
