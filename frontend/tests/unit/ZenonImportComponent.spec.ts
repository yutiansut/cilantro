import { mount, createLocalVue } from '@vue/test-utils';
import Buefy from 'buefy';
import sinon from 'sinon';
import ZenonImportComponent from '@/job/ingest-journal/forms/ZenonImportComponent.vue';
import { ZenonRecord, ZenonAuthors } from '@/job/ingest-journal/ZenonImport.ts';

const localVue = createLocalVue();
localVue.use(Buefy);

describe('ZenonImportComponent', () => {
    const searchMock = sinon.spy();
    let wrapper = initWrapper();

    function initWrapper() {
        return mount<ZenonImportComponent>(ZenonImportComponent, {
            localVue,
            methods: {
                search: searchMock
            }
        });
    }

    beforeEach(() => {
        wrapper = initWrapper();
    });

    it('renders search field and button', () => {
        expect(wrapper.find('input').exists()).toBe(true);
        expect(wrapper.find('button').exists()).toBe(true);
    });

    it('search button disabled before term entered', () => {
        expect(wrapper.find('button').attributes('disabled')).toBe('disabled');
        wrapper.setData({ searchTerm: 'aa' });
        expect(wrapper.find('button').attributes('disabled')).toBe(undefined);
    });

    it('search only called when searchTerm available and button clicked', () => {
        // no click -> not called
        expect(searchMock.called).toBe(false);

        // button disabled
        wrapper.find('button').trigger('click');
        expect(searchMock.called).toBe(false);

        wrapper.setData({ searchTerm: 'aa' });
        wrapper.find('button').trigger('click');
        expect(searchMock.called).toBe(true);
    });

    it('show result table when results available', (done) => {
        const testSearchResults = {
            id: '111',
            title: 'test-title',
            authors: {
                primary: {},
                secondary: {},
                corporate: {}
            },
            formats: [],
            languages: [],
            series: [],
            subjects: []
        };

        expect(wrapper.find('table').exists()).toBe(false);

        wrapper.setData({
            searchResults: [testSearchResults]
        });

        wrapper.vm.$nextTick(() => {
            expect(wrapper.find('table').exists()).toBe(true);
            done();
        });
    });
});
