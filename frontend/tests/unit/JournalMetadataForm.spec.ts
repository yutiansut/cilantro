import { mount, createLocalVue } from '@vue/test-utils';
import Buefy from 'buefy';
import JournalMetadataForm from '@/job/ingest-journal/forms/JournalMetadataForm.vue';
import { JournalIssueMetadata } from '@/job/ingest-journal/JournalImportParameters';

const localVue = createLocalVue();
localVue.use(Buefy);

describe('JournalMetadataForm.vue', () => {
    const journalMetadata: JournalIssueMetadata = {
        zenon_id: 12345,
        volume: 1,
        year: 2018,
        number: 0,
        description: '[PDFs teilweise verf\u00fcgbar]',
        ojs_journal_code: 'aa'
    };
    const wrapper = mount(JournalMetadataForm, {
        localVue,
        propsData: { metadata: journalMetadata }
    });

    it('renders input element', () => {
        const el = wrapper.find('input');
        expect(el.is('input')).toBe(true);
    });
});
